from lxml import etree
import sys
import glob

with open(sys.argv[1], 'br') as f:
    continent = etree.XML(f.read())
g = continent.find('{http://www.w3.org/2000/svg}g')
selected_country = None
for country in g:
    country_name = country.get('id')
    if glob.glob(country_name + '.svg'):
        g.remove(country)
    elif selected_country is None:
        selected_country = country_name
    else:
        g.remove(country)


with open(selected_country + '.svg', 'wb') as f:
    f.write(etree.tostring(continent))


