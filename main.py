import re
import json
from multiprocessing import Pool
import requests
import urllib3
from bs4 import BeautifulSoup as bs4


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
}

def get_book(id):
    url = f'https://www.wenku8.net/book/{id}.htm'
    r = requests.get(url, headers=headers, verify=False)
    r.encoding = "gbk"
    html = r.text
    if "错误原因：对不起，该文章不存在！" in html:
        raise ValueError("")

    soup = bs4(html, 'lxml')
    content = soup.find('div', id='content')

    try:
        name_tag = content.select_one('span[style*="font-size:16px"] b')
        name = name_tag.get_text(strip=True) if name_tag else "無書名"
    except:
        name = "無書名"

    try:
        wenku_td = content.find('td', string=lambda t: t and '文库分类' in t)
        info_tr = wenku_td.find_parent('tr') if wenku_td else None
        info_tds = info_tr.find_all('td') if info_tr else []
    except:
        info_tds = []

    publish = "未知分類"
    author = "未知作者"
    state = "未知狀態"
    last_update = "未知時間"
    length = "未知長度"
    try:
        publish = info_tds[0].get_text(strip=True).replace("文库分类：", "")
    except:
        pass

    try:
        author = info_tds[1].get_text(strip=True).replace("小说作者：", "")
    except:
        pass

    try:
        state = info_tds[2].get_text(strip=True).replace("文章状态：", "")
    except:
        pass

    try:
        last_update = info_tds[3].get_text(strip=True).replace("最后更新：", "")
    except:
        pass

    try:
        length = info_tds[4].get_text(strip=True).replace("全文长度：", "")
    except:
        pass

    try:
        img_tag = content.find('img')
        img = img_tag['src'] if img_tag else ''
    except:
        img = ''

    try:
        description_span = content.select('span[style*="font-size:14px;"]')
        raw_html = description_span[-1].decode_contents()
        lines = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.IGNORECASE).splitlines()
        description = '\n'.join(line.strip() for line in lines if line.strip())
    except:
        description = '無簡介'

    try:
        content_anchor = content.find('a', string='小说目录')
        content = content_anchor['href'] if content_anchor else ""
    except:
        content = ""

    tags = []
    try:
        tag_span = soup.find('span', string=lambda text: text and 'Tags' in text)
        if tag_span:
            tags_text = tag_span.get_text(strip=True)
            tags = tags_text.split('：')[-1].split()
    except:
        pass

    return {
        'id': id,
        'name': name,
        'publish': publish,
        'author': author,
        'status': state,
        'description': description,
        'last_update': last_update,
        'length': length,
        'thumbnail': img,
        'contents': content,
        'tags': tags
    }


def worker(id):
    try:
        return get_book(id)
    except ValueError:
        return None
    except Exception as e:
        print(f"Error on {id} {e}")

def main():
    with Pool() as p:
        results = p.map(worker, range(1, 9999))
    results = [r for r in results if r is not None]
    results.sort(key=lambda x: x['id'])

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
