from detect import detect_checkboxes

img = "./predict3.jpg"

data = detect_checkboxes(source=img)

if not data:
    print("Not found")
else:
    for item in data:
        cls = item['class']
        x1, y1, x2, y2 = item['box']

        if cls == 'checked':
            print(f"Found a checkbox! x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}") 
