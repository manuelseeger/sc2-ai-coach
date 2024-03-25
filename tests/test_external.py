from external.fast_ssim.ssim import ssim
from os.path import join
from rich import print
import cv2
from time import time

FIXTURES_DIR = 'tests/fixtures'

def test_performance_ssim():

    candidate_file = 'kat_1.png'
    compare_files = ['kat_1.png', 'kat_2.png', 'kat_master.png', 'kat_unranked.png']

    candidate = cv2.imread(join(FIXTURES_DIR, candidate_file))

    compares = {}

    for compare_file in compare_files:
        compare = cv2.imread(join(FIXTURES_DIR, compare_file))
        compares[compare_file] = compare

    start = time()
    for compare_file, compare in compares.items():
        score = ssim(candidate, compare)
        print(f'{compare_file}: {score}')
    end = time()
    print(f'Elapsed time: {end - start}')
