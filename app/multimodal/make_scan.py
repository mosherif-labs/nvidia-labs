from PIL import Image, ImageDraw, ImageFont

lines = [
    "FIRST HARBOUR BANK  -  ACCOUNT STATEMENT",
    "Account holder: Dana Kovacs        Account: A-1001",
    "IBAN: GB29 NWBK 6016 1331 9268 19   Period: 2026-08-01 to 2026-08-31",
    "",
    "Date        Description                    Amount (GBP)",
    "2026-08-03  CASH DEPOSIT  BRANCH 12             9,500.00",
    "2026-08-05  CASH DEPOSIT  BRANCH 12             9,200.00",
    "2026-08-06  TRANSFER OUT  ORBIT TRADING LTD   -18,000.00",
    "2026-08-09  CASH DEPOSIT  BRANCH 7              9,900.00",
    "2026-08-12  CASH DEPOSIT  BRANCH 12             9,000.00",
    "2026-08-13  TRANSFER OUT  ORBIT TRADING LTD   -18,500.00",
]
font = ImageFont.load_default(size=22)
img = Image.new("RGB", (1000, 420), "white")
draw = ImageDraw.Draw(img)
for i, line in enumerate(lines):
    draw.text((30, 25 + i * 34), line, fill="black", font=font)
img.rotate(1.2, expand=True, fillcolor="white").convert("L").save(
    "statement_scan.png", optimize=True
)
