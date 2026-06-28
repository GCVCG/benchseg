#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
#SBATCH -J segman_fs103
#SBATCH -o logs/segman_fs103_%j.out
#SBATCH -e logs/segman_fs103_%j.out
#SBATCH --requeue
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
SEG=$ROOT/baselines/SegMan/segmentation
WORK=$ROOT/work_dirs/segman_b_foodseg103_80k
CFG=local_configs/segman/base/segman_b_foodseg103.py
cd "$ROOT"
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
mkdir -p "$WORK" logs
# make data_root='data/FoodSeg103/Images/' resolve from cwd=$SEG
ln -sfn "$ROOT/data" "$SEG/data"
# idempotent mmcv 1.7.2 + torch 2.x fix: scatter _get_stream() needs torch.device, not int
MMF="$ROOT/venvs/segman21/lib/python3.10/site-packages/mmcv/parallel/_functions.py"
python3 - "$MMF" <<'PYPATCH'
import sys
f = sys.argv[1]; s = open(f).read()
old = "streams = [_get_stream(device) for device in target_gpus]"
new = ("streams = [_get_stream(torch.device(\"cuda\", device) "
       "if isinstance(device, int) else device) for device in target_gpus]")
if old in s:
    open(f, "w").write(s.replace(old, new)); print("mmcv _functions patch applied")
else:
    print("mmcv _functions patch already present" if new in s else "mmcv _functions patch: pattern not found")
PYPATCH
# idempotent mmcv 1.7.2 + torch 2.x fix #2: DDP eval forward references the
# removed _use_replicated_tensor_module attribute -> guard with getattr
MMD="$ROOT/venvs/segman21/lib/python3.10/site-packages/mmcv/parallel/distributed.py"
python3 - "$MMD" <<'PYPATCH2'
import sys
f = sys.argv[1]; s = open(f).read()
old = ('        module_to_run = self._replicated_tensor_module if \\\n'
       '            self._use_replicated_tensor_module else self.module')
new = ('        module_to_run = getattr(self, "_replicated_tensor_module", self.module) if \\\n'
       '            getattr(self, "_use_replicated_tensor_module", False) else self.module')
if old in s:
    open(f, "w").write(s.replace(old, new)); print("mmcv distributed patch applied")
else:
    print("mmcv distributed patch already present" if new in s else "mmcv distributed patch: pattern not found")
PYPATCH2
# auto-resume across maintenance preemption / requeue
RESUME=""; [ -f "$WORK/latest.pth" ] && RESUME="--resume-from $WORK/latest.pth"
echo "### resume='$RESUME' work=$WORK ###"

singularity exec --nv --bind "$ROOT":"$ROOT" \
  --env CUDA_HOME=/usr/local/cuda \
  --env LD_LIBRARY_PATH=$ROOT/xlibs:/.singularity.d/libs:/usr/local/cuda/lib64 \
  --env TRITON_LIBCUDA_PATH=/.singularity.d/libs \
  --env PYTHONPATH=$SEG \
  --pwd "$SEG" "$ROOT/containers/pytorch21_devel.sif" \
  "$ROOT/venvs/segman21/bin/python" -m torch.distributed.launch \
    --nproc_per_node=2 --master_port=$((RANDOM+20000)) \
    tools/train.py "$CFG" --launcher pytorch --work-dir "$WORK" $RESUME

echo "### train exit=$? $(date) ###"
echo "### best ckpt:"; ls -t "$WORK"/best_mIoU_*.pth 2>/dev/null | head -1
