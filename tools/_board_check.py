import json, os

files = [
    r"Q:\Claudework\bridge base\web_frontend\data\board-korea.json",
    r"Q:\Claudework\bridge base\web_frontend\data\board-about.json",
    r"Q:\Claudework\bridge base\web_frontend\data\board-testimonials.json",
]

for f in files:
    size = os.path.getsize(f)
    try:
        with open(f, encoding='utf-8') as fp:
            data = json.load(fp)
        print(f"OK  {os.path.basename(f)}: {len(data)} posts, {size//1024}KB")
        if data:
            p0 = data[0]
            print(f"    first: id={p0.get('id')} sort={p0.get('sort_order')} title={str(p0.get('title',''))[:50]}")
            # check for images
            with_imgs = [p for p in data if p.get('image_paths') and p['image_paths'] != '[]']
            print(f"    posts with image_paths: {len(with_imgs)}")
    except Exception as e:
        print(f"ERR {os.path.basename(f)}: {e} ({size//1024}KB)")
