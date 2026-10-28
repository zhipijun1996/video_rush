from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from PIL import Image
from video_rush.graphics import graphic
from video_rush.footage import collect
from video_rush.common import sha


def test_explanatory_diagram_is_readable_editable_and_traceable(tmp_path):
    g={'layout':'diagram','elements':[
        {'type':'rect','bounds':[100,200,700,300]},
        {'type':'text','x':130,'y':240,'text':'入口 < 出口 & 有向路线','width':640},
        {'type':'line','points':[[850,300],[1100,300]],'arrow':True,'both':True}]}
    rows=collect(tmp_path,{'repository':'test/repo','assets':[{'id':'route','origin':'editorial','kind':'explanatory_diagram','graphic':g}]},tmp_path/'media')
    svg=tmp_path/rows[0]['editable_svg']
    assert sha(svg)==rows[0]['svg_sha256']
    root=ET.parse(svg).getroot()
    ns={'s':'http://www.w3.org/2000/svg'}
    assert root.find('s:text',ns).text=='入口 < 出口 & 有向路线'
    assert len(root.findall('s:polygon',ns))==2
    im=Image.open(rows[0]['local_path'])
    assert im.size==(1920,1080) and im.getpixel((850,300))!=(16,27,43)
    with pytest.raises(ValueError,match='too long'):
        graphic(tmp_path/'bad.png',{'layout':'diagram','elements':[{'type':'text','x':10,'y':10,'text':'字'*100,'width':50}]})
    with pytest.raises(ValueError,match='outside canvas'):
        graphic(tmp_path/'bad.png',{'layout':'diagram','elements':[{'type':'rect','bounds':[1900,100,100,100]}]})
