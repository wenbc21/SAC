import os
import json
import random
import math
import torch
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn import metrics
from torchvision import transforms


def read_dataset(ori_root: str, split: str):
    # random.seed(0)  # 保证随机结果可复现
    root = os.path.join(ori_root, split)
    assert os.path.exists(root), "dataset root: {} does not exist.".format(root)

    # 遍历文件夹，一个文件夹对应一个类别
    classes = [cla for cla in os.listdir(root) if os.path.isdir(os.path.join(root, cla))]
    # 排序，保证各平台顺序一致
    classes.sort()
    # 生成类别名称以及对应的数字索引
    class_indices = dict((k, v) for v, k in enumerate(classes))
    json_str = json.dumps(dict((val, key) for key, val in class_indices.items()), indent=4)
    with open(os.path.join(ori_root, 'class_indices.json'), 'w') as json_file:
        json_file.write(json_str)

    images_path = []  # 存储所有图片路径
    images_label = []  # 存储图片对应索引信息
    every_class_num = []  # 存储每个类别的样本总数
    supported = [".jpg", ".JPG", ".png", ".PNG"]  # 支持的文件后缀类型
    # 遍历每个文件夹下的文件
    for cla in classes:
        cla_path = os.path.join(root, cla)
        # 遍历获取supported支持的所有文件路径
        images = [os.path.join(root, cla, i) for i in os.listdir(cla_path)
                  if os.path.splitext(i)[-1] in supported]
        # 排序，保证各平台顺序一致
        images.sort()
        # 获取该类别对应的索引
        image_class = class_indices[cla]
        # 记录该类别的样本数量
        every_class_num.append(len(images))

        for img_path in images:
            images_path.append(img_path)
            images_label.append(image_class)

    print("{} images were found in the dataset.".format(sum(every_class_num)))
    print("{} images for {}.".format(len(images_path), split))
    assert len(images_path) > 0, f"number of {split} images must greater than 0."

    return images_path, images_label

def augment_and_pad(self, image, target_size):
        # size transform
        width, height = image.size
        if width > height:
            new_width = target_size
            new_height = int(height * (target_size / width))
        else:
            new_height = target_size
            new_width = int(width * (target_size / height))
        
        augment_transform = transforms.Compose([
            transforms.Resize((new_height, new_width)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.ColorJitter(brightness=(0.75, 1.5), contrast=(1.25, 1.75)),
            transforms.RandomRotation(20)
        ])
        
        augmented_image = augment_transform(image)
        width, height = augmented_image.size

        if width > height:
            new_width = target_size
            new_height = int(height * (target_size / width))
        else:
            new_height = target_size
            new_width = int(width * (target_size / height))
        
        pad_height1 = (target_size - new_width) // 2
        pad_height2 = target_size - new_width - pad_height1
        pad_width1 = (target_size - new_height) // 2
        pad_width2 = target_size - new_height - pad_width1

        transform = transforms.Compose([
            transforms.Pad((pad_height1, pad_width1, pad_height2, pad_width2), fill=(0,)*self.channels),
            transforms.ToTensor(),
            transforms.Normalize(self.mean, self.std)
        ])
        
        padded_image = transform(augmented_image)
        
        return padded_image


def resize_and_pad(image, target_size, mean, std, img_channel):
    width, height = image.size

    if width > height:
        new_width = target_size
        new_height = int(height * (target_size / width))
    else:
        new_height = target_size
        new_width = int(width * (target_size / height))
    
    transform = transforms.Compose([
        transforms.Resize((new_height, new_width)),
    ])
    
    image = transform(image)
    
    width, height = image.size

    if width > height:
        new_width = target_size
        new_height = int(height * (target_size / width))
    else:
        new_height = target_size
        new_width = int(width * (target_size / height))
    
    pad_height1 = (target_size - new_width) // 2
    pad_height2 = target_size - new_width - pad_height1
    pad_width1 = (target_size - new_height) // 2
    pad_width2 = target_size - new_height - pad_width1

    transform = transforms.Compose([
        transforms.Pad((pad_height1, pad_width1, pad_height2, pad_width2), fill=(0,)*img_channel),
        transforms.ToTensor(),
        transforms.Normalize(mean, std)
    ])
    
    padded_image = transform(image)
    
    return padded_image


def pad_ori(image, target_size, mean, std, img_channel):
    width, height = image.size

    if width > height:
        new_width = target_size
        new_height = int(height * (target_size / width))
    else:
        new_height = target_size
        new_width = int(width * (target_size / height))
    
    transform = transforms.Compose([
        transforms.Resize((new_height, new_width)),
    ])
    
    image = transform(image)
    
    width, height = image.size

    if width > height:
        new_width = target_size
        new_height = int(height * (target_size / width))
    else:
        new_height = target_size
        new_width = int(width * (target_size / height))
    
    pad_height1 = (target_size - new_width) // 2
    pad_height2 = target_size - new_width - pad_height1
    pad_width1 = (target_size - new_height) // 2
    pad_width2 = target_size - new_height - pad_width1

    transform = transforms.Compose([
        transforms.Pad((pad_height1, pad_width1, pad_height2, pad_width2), fill=(0,)*img_channel),
    ])
    
    padded_image = transform(image)
    
    return padded_image



def create_lr_scheduler(
    optimizer,
    num_step: int,
    epochs: int,
    warmup=True,
    warmup_epochs=1,
    warmup_factor=1e-3,
    end_factor=1e-6
    ):
    assert num_step > 0 and epochs > 0
    if warmup is False:
        warmup_epochs = 0

    def f(x):
        if warmup is True and x <= (warmup_epochs * num_step):
            alpha = float(x) / (warmup_epochs * num_step)
            # warmup过程中lr倍率因子从warmup_factor -> 1
            return warmup_factor * (1 - alpha) + alpha
        else:
            current_step = (x - warmup_epochs * num_step)
            cosine_steps = (epochs - warmup_epochs) * num_step
            # warmup后lr倍率因子从1 -> end_factor
            return ((1 + math.cos(current_step * math.pi / cosine_steps)) / 2) * (1 - end_factor) + end_factor

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=f)


def get_params_groups(model: torch.nn.Module, weight_decay: float = 1e-5):
    # 记录optimize要训练的权重参数
    parameter_group_vars = {"decay": {"params": [], "weight_decay": weight_decay},
                            "no_decay": {"params": [], "weight_decay": 0.}}

    # 记录对应的权重名称
    parameter_group_names = {"decay": {"params": [], "weight_decay": weight_decay},
                             "no_decay": {"params": [], "weight_decay": 0.}}

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue  # frozen weights

        if len(param.shape) == 1 or name.endswith(".bias"):
            group_name = "no_decay"
        else:
            group_name = "decay"

        parameter_group_vars[group_name]["params"].append(param)
        parameter_group_names[group_name]["params"].append(name)

    # print("Param groups = %s" % json.dumps(parameter_group_names, indent=2))
    return list(parameter_group_vars.values())


def get_mean_std(path: str) :
    img_channels = 3
    img_names = path
    cumulative_mean = np.zeros(img_channels)
    cumulative_std = np.zeros(img_channels)

    for img_name in img_names:
        img = np.array(Image.open(img_name)) / 255.
        for d in range(3):
            cumulative_mean[d] += img[:, :, d].mean()
            cumulative_std[d] += img[:, :, d].std()

    mean = cumulative_mean / len(img_names)
    std = cumulative_std / len(img_names)
    
    return mean, std


def tensor2img(tensor,heatmap=False,shape=(224,224)):
    tensor = tensor.cpu()
    np_arr=tensor.detach().numpy()#[0]
    #对数据进行归一化
    if np_arr.max()>1 or np_arr.min()<0:
        np_arr=np_arr-np_arr.min()
        np_arr=np_arr/np_arr.max()
    #np_arr=(np_arr*255).astype(np.uint8)
    if np_arr.shape[0]==1:
        np_arr=np.concatenate([np_arr,np_arr,np_arr],axis=0)
    np_arr=np_arr.transpose((1,2,0))
    return np_arr


def plot_training_loss(train_losses, val_losses, args) :
    x = np.linspace(1, args.epochs, args.epochs)
    plt.plot(x, np.array(train_losses), c='r', ls ='-',label = "train_loss")
    plt.plot(x, np.array(val_losses), c='b', ls ='-', label = "validation_loss")
    plt.xlabel("epoch")
    plt.ylabel("loss")
    plt.ylim((0.0, 1.0))
    plt.grid()
    plt.legend()
    plt.savefig(os.path.join(args.results_dir, f"fold{args.fold}_train_loss.png"))
    

def plot_confusion_matrix(y_true, y_pred, labels_name, title=None, thresh=0.5, axis_labels=None, s=""):
    # 利用sklearn中的函数生成混淆矩阵并归一化
    
    y_p = []
    for i in y_pred :
        if i > thresh :
            y_p.append(1)
        else: 
            y_p.append(0)
    y_pred = y_p
    
    cm = metrics.confusion_matrix(y_true, y_pred, labels=labels_name, sample_weight=None)  # 生成混淆矩阵 
    cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]  # 归一化

    # 画图，如果希望改变颜色风格，可以改变此部分的cmap=pl.get_cmap('Blues')处
    plt.imshow(cm, interpolation='nearest', cmap=plt.get_cmap('Blues'))
    plt.colorbar()  # 绘制图例

    # 图像标题
    if title is not None:
        plt.title(title)
    # 绘制坐标
    num_local = np.array(range(len(labels_name)))
    if axis_labels is None:
        axis_labels = ["N", "Y"]
    plt.xticks(num_local, axis_labels)  # 将标签印在x轴坐标上， 并倾斜45度
    plt.yticks(num_local, axis_labels)  # 将标签印在y轴坐标上
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

    # 将百分比打印在相应的格子内，大于thresh的用白字，小于的用黑字
    for i in range(np.shape(cm)[0]):
        for j in range(np.shape(cm)[1]):
            if int(cm[i][j] * 100 + 0.5) > 0:
                plt.text(j, i, format(int(cm[i][j] * 100 + 0.5), 'd') + '%',
                        ha="center", va="center",
                        color="white" if cm[i][j] > thresh else "black")  # 如果要更改颜色风格，需要同时更改此行
    # 显示
    plt.savefig(s)


def plot_test_metrics(test_images_label, test_images_predict, results_dir, model_config) :
    # AUROC
    fpr1, tpr1, thresholds = metrics.roc_curve(test_images_label, test_images_predict)
    roc_auc1 = metrics.auc(fpr1, tpr1)  # the value of roc_auc1
    plt.plot(fpr1, tpr1, 'r', label='AUROC = %0.4f' % roc_auc1)
    plt.plot([0.0, 1.0], [0.0, 1.0], 'gray', linestyle='--')
    plt.legend(loc='lower right')
    plt.xlim([-0.05, 1.05])  # the range of x-axis
    plt.ylim([-0.05, 1.05])  # the range of y-axis
    plt.xlabel('False Positive Rate')  # the name of x-axis
    plt.ylabel('True Positive Rate')  # the name of y-axis
    plt.title(model_config + ' AUROC')  # the title of figure
    plt.savefig(os.path.join(results_dir, model_config + "_AUROC.png"))
    # plt.show()
    plt.close()

    # AUPRC
    precision1, recall1, _ = metrics.precision_recall_curve(test_images_label, test_images_predict)
    aupr1 = metrics.auc(recall1, precision1)  # the value of roc_auc1
    plt.plot(recall1, precision1, 'b', label='AUPRC = %0.4f' % aupr1)
    plt.plot([0.0, 1.0], [1.0, 0.0], 'gray', linestyle='--')
    plt.legend(loc='lower left')
    plt.xlim([-0.05, 1.05])  # the range of x-axis
    plt.ylim([-0.05, 1.05])  # the range of y-axis
    plt.xlabel('Recall')  # the name of x-axis
    plt.ylabel('Precision')  # the name of y-axis
    plt.title(model_config + ' AUPRC')  # the title of figure
    plt.savefig(os.path.join(results_dir, model_config + "_AUPRC.png"))
    # plt.show()
    plt.close()

    plot_confusion_matrix(
        test_images_label, 
        test_images_predict, 
        [0, 1], 
        title=model_config + " Confusion Matrix", 
        thresh=0.5, 
        axis_labels=None, 
        s=os.path.join(results_dir, model_config + "_Confusion_Matrix.png")
    )

    return roc_auc1, aupr1
