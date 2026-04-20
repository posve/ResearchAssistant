import timeit
import re

text = "This is a sample text with a DOI: 10.1234/abcde and some other text."

def with_compile_in_loop():
    doi_pattern = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
    match = doi_pattern.search(text)

DOI_PATTERN = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)

def with_compile_outside():
    match = DOI_PATTERN.search(text)

if __name__ == "__main__":
    n = 100000
    t1 = timeit.timeit(with_compile_in_loop, number=n)
    t2 = timeit.timeit(with_compile_outside, number=n)
    print(f"Inside loop: {t1:.4f} seconds")
    print(f"Outside loop: {t2:.4f} seconds")
    print(f"Improvement: {(t1-t2)/t1*100:.2f}%")
