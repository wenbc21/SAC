from PIL import Image
import torch
from torchvision import transforms
from torch.utils.data import Dataset
import matplotlib.pyplot as plt
import torchvision.transforms.functional as F

class MyDataSet(Dataset):

    def __init__(self, images_path: list, images_class: list, is_train: bool, mean, std):
        self.images_path = images_path
        self.images_class = images_class
        self.mean = mean
        self.std = std
        self.channels = len(mean)

    # 定义变换
    def augment_and_pad(self, image, target_size):
        # size transform
        width, height = image.size
        if width > height:
            new_width = target_size
            new_height = int(height * (target_size / width))
        else:
            new_height = target_size
            new_width = int(width * (target_size / height))
        
        # 创建增强变换
        augment_transform = transforms.Compose([
            transforms.Resize((new_height, new_width)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.ColorJitter(brightness=(0.75, 1.5), contrast=(1.25, 1.75)),
            transforms.RandomRotation(20)
        ])
        
        # 应用增强变换
        augmented_image = augment_transform(image)
        
        # 获取增强后的图像尺寸
        width, height = augmented_image.size

        if width > height:
            # 图像较宽
            new_width = target_size
            new_height = int(height * (target_size / width))
        else:
            # 图像较高
            new_height = target_size
            new_width = int(width * (target_size / height))
        
        pad_height1 = (target_size - new_width) // 2
        pad_height2 = target_size - new_width - pad_height1
        pad_width1 = (target_size - new_height) // 2
        pad_width2 = target_size - new_height - pad_width1

        # 创建变换
        transform = transforms.Compose([
            # transforms.Resize((new_height, new_width)),  # 首先调整大小
            transforms.Pad((pad_height1, pad_width1, pad_height2, pad_width2), fill=(0,)*self.channels),
            transforms.ToTensor(),
            transforms.Normalize(self.mean, self.std)
        ])
        
        # 应用调整大小和填充变换
        padded_image = transform(augmented_image)
        
        return padded_image

    def __len__(self):
        return len(self.images_path)

    def __getitem__(self, item):
        img = Image.open(self.images_path[item])
        if self.channels == 1 :
            img = img.convert('L')
        
        img = self.augment_and_pad(img, 224)
        label = self.images_class[item]

        return img, label

    @staticmethod
    def collate_fn(batch):
        images, labels = tuple(zip(*batch))
        images = torch.stack(images, dim=0)
        labels = torch.as_tensor(labels)
        return images, labels
