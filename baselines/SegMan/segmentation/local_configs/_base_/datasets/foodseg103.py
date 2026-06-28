# FoodSeg103 dataset (104 classes: 0=background, 1..103=ingredients).
# Mirrors the protocol used for the other FoodSeg103-trained models in this repo
# (CustomDataset, data_root=data/FoodSeg103/Images/, reduce_zero_label=False so
# background is a real evaluated class), and the dense mIoU/mAcc eval in
# src/foodseg103_eval.py. Pipelines follow the SegMAN ADE recipe (512x512 crop).
dataset_type = 'CustomDataset'
data_root = 'data/FoodSeg103/Images/'

FOODSEG_CLASSES = (
    'background', 'candy', 'egg tart', 'french fries', 'chocolate', 'biscuit',
    'popcorn', 'pudding', 'ice cream', 'cheese butter', 'cake', 'wine',
    'milkshake', 'coffee', 'juice', 'milk', 'tea', 'almond', 'red beans',
    'cashew', 'dried cranberries', 'soy', 'walnut', 'peanut', 'egg', 'apple',
    'date', 'apricot', 'avocado', 'banana', 'strawberry', 'cherry', 'blueberry',
    'raspberry', 'mango', 'olives', 'peach', 'lemon', 'pear', 'fig', 'pineapple',
    'grape', 'kiwi', 'melon', 'orange', 'watermelon', 'steak', 'pork',
    'chicken duck', 'sausage', 'fried meat', 'lamb', 'sauce', 'crab', 'fish',
    'shellfish', 'shrimp', 'soup', 'bread', 'corn', 'hamburg', 'pizza',
    'hanamaki baozi', 'wonton dumplings', 'pasta', 'noodles', 'rice', 'pie',
    'tofu', 'eggplant', 'potato', 'garlic', 'cauliflower', 'tomato', 'kelp',
    'seaweed', 'spring onion', 'rape', 'ginger', 'okra', 'lettuce', 'pumpkin',
    'cucumber', 'white radish', 'carrot', 'asparagus', 'bamboo shoots',
    'broccoli', 'celery stick', 'cilantro mint', 'snow peas', 'cabbage',
    'bean sprouts', 'onion', 'pepper', 'green beans', 'French beans',
    'king oyster mushroom', 'shiitake', 'enoki mushroom', 'oyster mushroom',
    'white button mushroom', 'salad', 'other ingredients')
FOODSEG_PALETTE = [[(i * 37) % 256, (i * 91) % 256, (i * 173) % 256]
                   for i in range(len(FOODSEG_CLASSES))]

img_norm_cfg = dict(
    mean=[123.675, 116.28, 103.53], std=[58.395, 57.12, 57.375], to_rgb=True)
crop_size = (512, 512)
train_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='LoadAnnotations', reduce_zero_label=False),
    dict(type='Resize', img_scale=(2048, 512), ratio_range=(0.5, 2.0)),
    dict(type='RandomCrop', crop_size=crop_size, cat_max_ratio=0.75),
    dict(type='RandomFlip', prob=0.5),
    dict(type='PhotoMetricDistortion'),
    dict(type='Normalize', **img_norm_cfg),
    dict(type='Pad', size=crop_size, pad_val=0, seg_pad_val=255),
    dict(type='DefaultFormatBundle'),
    dict(type='Collect', keys=['img', 'gt_semantic_seg']),
]
test_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(
        type='MultiScaleFlipAug',
        img_scale=(2048, 512),
        flip=False,
        transforms=[
            dict(type='AlignedResize', keep_ratio=True, size_divisor=32),
            dict(type='RandomFlip'),
            dict(type='Normalize', **img_norm_cfg),
            dict(type='ImageToTensor', keys=['img']),
            dict(type='Collect', keys=['img']),
        ])
]
data = dict(
    samples_per_gpu=4,
    workers_per_gpu=4,
    train=dict(
        type=dataset_type,
        data_root=data_root,
        img_dir='img_dir/train',
        ann_dir='ann_dir/train',
        classes=FOODSEG_CLASSES,
        palette=FOODSEG_PALETTE,
        reduce_zero_label=False,
        pipeline=train_pipeline),
    val=dict(
        type=dataset_type,
        data_root=data_root,
        img_dir='img_dir/test',
        ann_dir='ann_dir/test',
        classes=FOODSEG_CLASSES,
        palette=FOODSEG_PALETTE,
        reduce_zero_label=False,
        pipeline=test_pipeline),
    test=dict(
        type=dataset_type,
        data_root=data_root,
        img_dir='img_dir/test',
        ann_dir='ann_dir/test',
        classes=FOODSEG_CLASSES,
        palette=FOODSEG_PALETTE,
        reduce_zero_label=False,
        pipeline=test_pipeline))
