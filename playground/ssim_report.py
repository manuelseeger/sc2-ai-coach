import sys

sys.path.append("..")

import glob

import numpy as np
from PIL import Image

from external.fast_ssim.ssim import ssim

list_of_files = glob.glob("obs/screenshots/portraits/*.png")
# list_of_files = list_of_files[:5]

results = []

for l in list_of_files:
    for r in list_of_files:
        if l == r:
            continue
        img1 = Image.open(l)
        img2 = Image.open(r)

        # Calculate SSIM
        score = ssim(np.array(img1), np.array(img2))

        # Save results
        results.append((l, r, score))

        img1.close()
        img2.close()
        print()

# filter out perfect matches
results = [(l, r, score) for l, r, score in results if score < 0.99]

results_html = [
    '<tr><td><img src="%s"/></td><td><img src="%s"/></td><td>%s</td></tr>'
    % (l, r, score)
    for l, r, score in sorted(results, key=lambda x: x[2], reverse=True)
]

# Save results
report = """<html>
<head>
    <style>
        table {
            border-collapse: collapse;
            
        }

        th, td {
            border: 1px solid black;
            text-align: left;
            padding: 8px;
        }

        th {
            background-color: #f2f2f2;
        }
    </style>
</head>
<body>
    <table>
        <tr>
            <th>Image 1</th>
            <th>Image 2</th>
            <th>SSIM</th>
        </tr>
%s
    </table>
</body>
</html>
""" % "\n".join(
    results_html
)

with open("ssim_report.html", "w") as f:
    f.write(report)
    print("Report saved to ssim_report.html")
