# SegMAN-B finetuned on FoodSeg103 (104 classes), 80k iters.
# Mirrors the official segman_b_ade.py recipe (AdamW lr=6e-5, wd=0.01, paramwise
# head lr_mult=10, 1500-iter linear warmup, poly decay) but on the FoodSeg103
# dataset with num_classes=104, initialised from the ImageNet-1k pretrained
# SegMAN-B encoder so the comparison with the other FoodSeg103-trained models
# (FPN/CCNet/SeTR, all 80k from ImageNet backbones) is apples-to-apples.
# Run from baselines/SegMan/segmentation (relative data/ symlink + pretrained/).
_base_ = [
    '../../_base_/models/segman.py',
    '../../_base_/datasets/foodseg103.py',
    '../../_base_/default_runtime.py',
    '../../_base_/schedules/schedule_80k_adamw.py'
]

norm_cfg = dict(type='SyncBN', requires_grad=True)
model = dict(
    type='EncoderDecoder',
    backbone=dict(
        type='SegMANEncoder_b',
        pretrained='pretrained/SegMAN_Encoder_b.pth.tar',
        style='pytorch'),
    decode_head=dict(
        type='SegMANDecoder',
        in_channels=[96, 160, 364, 560],
        in_index=[0, 1, 2, 3],
        channels=180,
        feat_proj_dim=320,
        dropout_ratio=0.1,
        num_classes=104,
        norm_cfg=norm_cfg,
        align_corners=False,
        loss_decode=dict(type='CrossEntropyLoss', use_sigmoid=False, loss_weight=1.0)),
    train_cfg=dict(),
    test_cfg=dict(mode='whole')
)

# optimizer (official SegMAN-B recipe)
optimizer = dict(_delete_=True, type='AdamW', lr=0.00006, betas=(0.9, 0.999),
                 weight_decay=0.01,
                 paramwise_cfg=dict(custom_keys={'pos_block': dict(decay_mult=0.),
                                                 'norm': dict(decay_mult=0.),
                                                 'head': dict(lr_mult=10.)
                                                 }))
lr_config = dict(_delete_=True, policy='poly',
                 warmup='linear',
                 warmup_iters=1500,
                 warmup_ratio=1e-6,
                 power=1.0, min_lr=0.0, by_epoch=False)

# 2-GPU finetune: 4 per GPU x 2 = total batch size 8. Matches the house FoodSeg103
# standard (CCNet: samples_per_gpu=2 x 4 GPUs = 8, 80k iters) and fits the H100 NVL
# (~53GB/GPU at crop 512); 8/GPU (~100GB) would OOM the H100. ~0.31s/iter -> ~7h.
data = dict(samples_per_gpu=4)
evaluation = dict(interval=4000, metric='mIoU', save_best='mIoU')
