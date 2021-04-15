#!/usr/bin/env python
#
# Read exported "Flow Sheet" and save stream names / numbers to both XML and CSV formats.
#
import pandas as pd
from lxml import etree as ET

flow_sheet_csv   = '/Volumes/Plevin1TB/Software/OPGEE/model/flow_sheet.csv'
stream_xml_path  = '/Users/rjp/repos/OPGEEv4/opgee/etc/streams.xml'
streams_csv_path = '/Users/rjp/repos/OPGEEv4/opgee/etc/streams.csv'

df = pd.read_csv(flow_sheet_csv, index_col=None)

tups = [[c, df.loc[0, c]] for c in df.columns if c.isdigit()]
for tup in tups:
    if pd.isna(tup[1]):
        tup[1] = f"Reserved-{tup[0]}"

root = ET.Element('Streams')
for number, name in tups:
    stream = ET.SubElement(root, 'Stream', attrib={'name': name, 'number': number})
    stream.text = ' '
    #t = ET.SubElement(stream, 'Temperature', attrib={'unit': 'degF'})
    #t.text = '0'
    #p = ET.SubElement(stream, 'Pressure', attrib={'unit': 'psia'})
    #p.text = '0'

tree = ET.ElementTree(root)
tree.write(stream_xml_path, xml_declaration=True, pretty_print=True, encoding='utf-8')

tups2 = [(int(number), name) for number, name in tups]
df = pd.DataFrame(data=tups2, columns=['number', 'name']).set_index('number')
df.to_csv(streams_csv_path)
