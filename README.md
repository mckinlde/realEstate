python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt
playwright install

python zillow_addresses.py


### Good example:
# https://www.arcgis.com/apps/View/index.html?appid=b5118cb926c64ebeac59c8d0b01f6e45
# 133 18th Avenue Northwest, Center Point, AL 35215

### Bad example:
# 3076 Travis Rd Memphis, TN 38109
# Shelby County, TN
# https://gis.shelbycountytn.gov/Html5Viewer/Index.html?viewer
