# retrain_model.py
from app.core.database import SessionLocal, RetrainingSample
from app.services.ai_service import AIService
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, AdamW
import tensorflow as tf
import socketio
import librosa
import numpy as np
import cv2

db = SessionLocal()
samples = db.query(RetrainingSample).all()
texts = [s.data for s in samples if s.content_type == "text"]
labels = [s.label for s in samples if s.content_type == "text"]

ai_service = AIService()
ai_service.retrain_text_model(texts, labels)

class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

def retrain_pytorch_model(texts, labels):
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)
    dataset = TextDataset(texts, labels, tokenizer)
    loader = DataLoader(dataset, batch_size=8, shuffle=True)

    optimizer = AdamW(model.parameters(), lr=2e-5)
    model.train()
    for epoch in range(3):
        for batch in loader:
            optimizer.zero_grad()
            outputs = model(**{k: v for k, v in batch.items() if k != 'labels'}, labels=batch['labels'])
            loss = outputs.loss
            loss.backward()
            optimizer.step()
    model.save_pretrained("pytorch_model")
    tokenizer.save_pretrained("pytorch_model")

def retrain_tf_image_model(image_paths, labels):
    # Load images and preprocess
    images = [tf.image.decode_image(tf.io.read_file(p)) for p in image_paths]
    images = [tf.image.resize(img, [224, 224]) for img in images]
    images = tf.stack(images)
    labels = tf.convert_to_tensor(labels)

    # Build a simple model
    model = tf.keras.applications.MobileNetV2(weights=None, input_shape=(224,224,3), classes=2)
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    model.fit(images, labels, epochs=3)
    model.save("tf_image_model")

def extract_audio_features(audio_path):
    y, sr = librosa.load(audio_path)
    mfcc = librosa.feature.mfcc(y=y, sr=sr)
    return np.mean(mfcc.T, axis=0)

def retrain_tf_audio_model(audio_paths, labels):
    features = np.array([extract_audio_features(p) for p in audio_paths])
    labels = np.array(labels)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(features.shape[1],)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(2, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    model.fit(features, labels, epochs=3)
    model.save("tf_audio_model")

image_samples = db.query(RetrainingSample).filter(RetrainingSample.content_type == "image").all()
image_paths = [s.data for s in image_samples]
image_labels = [s.label for s in image_samples]
retrain_tf_image_model(image_paths, image_labels)

audio_samples = db.query(RetrainingSample).filter(RetrainingSample.content_type == "audio").all()
audio_paths = [s.data for s in audio_samples]
audio_labels = [s.label for s in audio_samples]
if audio_paths:
    retrain_tf_audio_model(audio_paths, audio_labels)

def extract_video_frames(video_path, frame_rate=1):
    vidcap = cv2.VideoCapture(video_path)
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    interval = int(fps // frame_rate)
    frames = []
    count = 0
    success, image = vidcap.read()
    while success:
        if count % interval == 0:
            frame_path = f"{video_path}_frame_{count}.jpg"
            cv2.imwrite(frame_path, image)
            frames.append(frame_path)
        success, image = vidcap.read()
        count += 1
    vidcap.release()
    return frames

video_samples = db.query(RetrainingSample).filter(RetrainingSample.content_type == "video").all()
video_paths = [s.data for s in video_samples]
video_labels = [s.label for s in video_samples]
all_frames = []
all_labels = []
for video_path, label in zip(video_paths, video_labels):
    frames = extract_video_frames(video_path)
    all_frames.extend(frames)
    all_labels.extend([label]*len(frames))
if all_frames:
    retrain_tf_image_model(all_frames, all_labels)

def send_retrain_notification(model_types, sample_counts):
    sio = socketio.Client()
    sio.connect("http://localhost:8000")
    sio.emit("model_retrained", {
        "message": "Models retrained",
        "models": model_types,
        "samples": sample_counts
    })
    sio.disconnect()

model_types = []
sample_counts = {}

if texts:
    retrain_pytorch_model(texts, labels)
    model_types.append("text")
    sample_counts["text"] = len(texts)
if image_paths:
    retrain_tf_image_model(image_paths, image_labels)
    model_types.append("image")
    sample_counts["image"] = len(image_paths)
if audio_paths:
    retrain_tf_audio_model(audio_paths, audio_labels)
    model_types.append("audio")
    sample_counts["audio"] = len(audio_paths)
if all_frames:
    model_types.append("video")
    sample_counts["video"] = len(all_frames)

send_retrain_notification(model_types, sample_counts)