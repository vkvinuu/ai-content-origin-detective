import os
from app.services.ml.model_manager import model_manager
from app.services.ml.inference import map_model_label
from PIL import Image

model_manager.load_models()

files = [
    ('4d87e7da-2750-4083-8864-f4c41b009883_raw.png', 'AI (DALL-E 3)'),
    ('3dbd6679-44e7-4818-8b5e-73a54ee24058_raw.png', 'AI (DALL-E 3)'),
    ('43f00947-2f9d-4078-83ea-53aded332108_raw.png', 'AI (DALL-E 3)'),
    ('be3d5f75-f9be-4d74-97d1-852c5f079a14_raw.jpg', 'Real (Camera)'),
    ('03469a83-2365-48a8-801f-c2cde3e22eb9_raw.jpeg', 'Real (Photo)'),
    ('22e7bc7b-2c38-4678-9e58-6bfb85d163e7_raw.jpg', 'Real (Photo)'),
    ('7c3ec1cb-f8f7-435e-9d40-2b4e8336d46a_raw.jpg', 'Real (Photo)'),
    ('cde36b44-edac-48c2-903d-38196ef69d38_raw.jpg', 'Real (Photo)')
]

print(f"{'Filename':<46} | {'Ground Truth':<14} | {'Ateeqq (SigLIP)':<18} | {'umm-maybe (ViT)':<18}")
print("-" * 105)

for fname, truth in files:
    p = os.path.join('uploads', fname)
    if not os.path.exists(p):
        continue
    img = Image.open(p).convert('RGB')
    cols = [f"{fname[:44]:<46}", f"{truth:<14}"]
    for m_cfg in model_manager.models_config:
        m_id = m_cfg['id']
        clf = model_manager.get_classifier(m_id)
        if clf:
            preds = clf(img)
            top = max(preds, key=lambda x: x['score'])
            norm = map_model_label(top['label'], m_id)
            cols.append(f"{norm[:4]} {top['score']:.3f} ({top['label']})")
        else:
            cols.append("N/A")
    print(" | ".join(cols))
