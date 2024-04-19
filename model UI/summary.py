# -*- coding: utf-8 -*-
"""Text_Summarization_Using_Transformer_T5_and_Pytorch_Lightning.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ucuM6r_Lu25CENLOlVme3JBmCFKzoYmT

<a href="https://colab.research.google.com/github/animesharma3/Text-Summarization-using-T5-transformers-and-Pytorch-Lightning/blob/main/Text_Summarization_Using_Transformer_T5_and_Pytorch_Lightning.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
"""

import json
import pandas as pd
import numpy as np
import torch
torch.cuda.empty_cache()
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger
from sklearn.model_selection import train_test_split
from termcolor import colored
from pytorch_lightning.strategies import DDPStrategy
import textwrap

from transformers import (
    AdamW,
    T5ForConditionalGeneration,
    T5TokenizerFast as T5Tokenizer
)
from tqdm.auto import tqdm

# Commented out IPython magic to ensure Python compatibility.
import seaborn as sns
from pylab import rcParams
import matplotlib.pyplot as plt
from matplotlib import rc

# %matplotlib inline
# %config InlineBackend.figure_format='retina'
sns.set(style='whitegrid', palette='muted', font_scale=1.2)
rcParams['figure.figsize'] = 16, 10
pl.seed_everything(42)

from datasets import load_dataset
dataset = load_dataset('d0rj/wikisum', split='train') # medical summarization dataset = ccdv/pubmed-summarization
full_dataset = dataset.train_test_split(test_size=0.2, shuffle=True)
dataset_train = full_dataset['train']
dataset_valid = full_dataset['test']


MODEL_NAME = 'google/flan-t5-base'
tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)

max_summary_length = 512
max_article_length = 2048

# Filter dataset based on summary and article lengths
dataset_train_filtered = dataset_train.filter(lambda example: len(example['summary']) <= max_summary_length and len(example['article']) <= max_article_length)
dataset_valid_filtered = dataset_valid.filter(lambda example: len(example['summary']) <= max_summary_length and len(example['article']) <= max_article_length)


train_df = pd.DataFrame(dataset_train_filtered)
test_df = pd.DataFrame(dataset_valid_filtered)

train_df = train_df[['article', 'summary']]
test_df = test_df[['article', 'summary']]

train_df.columns = ['text', 'summary']
train_df = train_df.dropna(subset=['text', 'summary'], axis=0)

test_df.columns = ['text', 'summary']
test_df = test_df.dropna(subset=['text', 'summary'], axis=0)


class NewsSummaryDataset(Dataset):
    def __init__(
        self,
        data: pd.DataFrame,
        tokenizer: T5Tokenizer,
        text_max_token_len: int = 2048,
        summary_max_token_len: int = 512
    ):
        self.tokenizer = tokenizer
        self.data = data
        self.text_max_token_len = text_max_token_len
        self.summary_max_token_len = summary_max_token_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index: int):
        data_row = self.data.iloc[index]

        text = data_row['text']

        text_encoding = tokenizer(
            text,
            max_length=self.text_max_token_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            add_special_tokens=True,
            return_tensors='pt'
        )

        summary_encoding = tokenizer(
            data_row['summary'],
            max_length=self.summary_max_token_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            add_special_tokens=True,
            return_tensors='pt'
        )

        labels = summary_encoding['input_ids']
        labels[labels == 0] = -100  # to make sure we have correct labels for T5 text generation

        return dict(
            text=text,
            summary=data_row['summary'],
            text_input_ids=text_encoding['input_ids'].flatten(),
            text_attention_mask=text_encoding['attention_mask'].flatten(),
            labels=labels.flatten(),
            labels_attention_mask=summary_encoding['attention_mask'].flatten()
        )

class NewsSummaryDataModule(pl.LightningDataModule):
    def __init__(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        tokenizer: T5Tokenizer,
        batch_size: int = 2,
        text_max_token_len: int = 2048,
        summary_max_token_len: int = 512
    ):
        super().__init__()

        self.train_df = train_df
        self.test_df = test_df
        self.batch_size = batch_size
        self.tokenizer = tokenizer
        self.text_max_token_len = text_max_token_len
        self.summary_max_token_len = summary_max_token_len

    def setup(self, stage=None):
        self.train_dataset = NewsSummaryDataset(
            self.train_df,
            self.tokenizer,
            self.text_max_token_len,
            self.summary_max_token_len
        )
        self.test_dataset = NewsSummaryDataset(
            self.test_df,
            self.tokenizer,
            self.text_max_token_len,
            self.summary_max_token_len
        )

    def train_dataloader(self):
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=2,
            prefetch_factor=2,
            pin_memory=True
        )

    def test_dataloader(self):
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=2,
            prefetch_factor=2,
            pin_memory=True
        )

    def val_dataloader(self):
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=2
        )

text_token_counts, summary_token_counts = [], []
batch_size = 2  # Adjust the batch size as needed

for i in range(0, len(train_df), batch_size):
    batch_text = train_df['text'].iloc[i:i+batch_size].tolist()
    batch_summary = train_df['summary'].iloc[i:i+batch_size].tolist()

    encoded_batch_text = tokenizer.batch_encode_plus(batch_text, padding=True, truncation=True, max_length=2048, return_tensors='pt')
    encoded_batch_summary = tokenizer.batch_encode_plus(batch_summary, padding=True, truncation=True, max_length=512, return_tensors='pt')

    batch_text_tokens = [len(input_ids) for input_ids in encoded_batch_text['input_ids']]
    batch_summary_tokens = [len(input_ids) for input_ids in encoded_batch_summary['input_ids']]

    text_token_counts.extend(batch_text_tokens)
    summary_token_counts.extend(batch_summary_tokens)

fig, (ax1, ax2) = plt.subplots(1, 2)
sns.histplot(text_token_counts, ax=ax1)
ax1.set_title('full text token counts')
sns.histplot(summary_token_counts, ax=ax2)

N_EPOCHS = 7
batch_size = 2

data_module = NewsSummaryDataModule(train_df, test_df, tokenizer)

from torch.cuda.amp import GradScaler, autocast
from torch.utils.checkpoint import checkpoint
from torch.nn.parallel import DataParallel
scaler = GradScaler()

class NewsSummaryModel(pl.LightningModule):
    def __init__(self):
        super().__init__()
        self.model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME, return_dict=True)
        self.model.to(self.device)
        self.accumulation_steps = 2

    def forward(self, input_ids, attention_mask, decoder_attention_mask, labels=None):
        def forward_pass(module, input_ids, attention_mask, decoder_attention_mask, labels):
            return module(
                input_ids,
                attention_mask=attention_mask,
                decoder_attention_mask=decoder_attention_mask,
                labels=labels
            )

        output = checkpoint(
            forward_pass,
            self.model,
            input_ids,
            attention_mask,
            decoder_attention_mask,
            labels
        )
        return output.loss, output.logits

    def training_step(self, batch, batch_idx):
        input_ids = batch['text_input_ids']
        attention_mask = batch['text_attention_mask']
        labels = batch['labels']
        labels_attention_mask = batch['labels_attention_mask']

        with autocast():
            loss, outputs = self(
                input_ids=input_ids,
                attention_mask=attention_mask,
                decoder_attention_mask=labels_attention_mask,
                labels=labels
            )

        self.log("train_loss", loss, prog_bar=True, logger=True)

        if (batch_idx + 1) % self.accumulation_steps == 0:
            self.manual_backward(loss)
            self.optimizer.step()
            self.optimizer.zero_grad()

        return loss

    def validation_step(self, batch, batch_size):
        input_ids = batch['text_input_ids']
        attention_mask = batch['text_attention_mask']
        labels = batch['labels']
        labels_attention_mask = batch['labels_attention_mask']

        loss, outputs = self(
            input_ids=input_ids,
            attention_mask=attention_mask,
            decoder_attention_mask=labels_attention_mask,
            labels=labels
        )

        self.log("val_loss", loss, prog_bar=True, logger=True)
        return loss

    def test_step(self, batch, batch_size):
        input_ids = batch['text_input_ids']
        attention_mask = batch['text_attention_mask']
        labels = batch['labels']
        labels_attention_mask = batch['labels_attention_mask']

        loss, outputs = self(
            input_ids=input_ids,
            attention_mask=attention_mask,
            decoder_attention_mask=labels_attention_mask,
            labels=labels
        )

        self.log("test_loss", loss, prog_bar=True, logger=True)
        return loss

    def configure_optimizers(self):
        return AdamW(self.parameters(), lr=0.0001)

# model = NewsSummaryModel()

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir ./lightning_logs
'''
import os

# Set the PYTORCH_CUDA_ALLOC_CONF environment variable
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

checkpoint_callback = ModelCheckpoint(
    dirpath='checkpoints',
    filename='best-checkpoint',
    save_top_k=1,
    verbose=True,
    monitor='val_loss',
    mode='min'
)

logger = TensorBoardLogger("lightning_logs", name='wikisum')

trainer = pl.Trainer(
    logger=None,
    callbacks=None,
    max_epochs=N_EPOCHS,
    accelerator="gpu",
    devices=1,
    accumulate_grad_batches=8,
    precision="16-mixed",
    strategy="auto",
    gradient_clip_val=1.0
)

trainer.fit(model, data_module)
'''