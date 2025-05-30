import time
import json
import enum
import base64
import urllib3
import requests
import datetime
from opencc import OpenCC
from multiprocessing import Pool
from bs4 import BeautifulSoup as bs4
from xml.etree import ElementTree as ET


cc = OpenCC("s2t")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Novel:
    class TYPE(enum.Enum):
        METADATA = enum.auto()
        DESCRIPTION = enum.auto()

    def __init__(self, aid: str):
        self.aid = aid
        self.base_url = "http://app.wenku8.com/android.php"
        self.web_url = "https://www.wenku8.net/book/{}.htm"
        self.version = "1.13"
        self.headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; IN2010 Build/RP1A.201005.001)",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def encode_base64(self, b: str):
        return base64.b64encode(b.encode("utf-8")).decode("utf-8")

    def get_encrypted_map(self, s):
        params = {}
        params["appver"] = self.version
        params["request"] = self.encode_base64(s)
        params["timetoken"] = str(int(time.time() * 1000))
        return params

    def get_encrypted_cv(self, s):
        data = self.get_encrypted_map(s)
        return dict(data)

    def get_text(self, root, path):
        try:
            return root.find(path).text
        except Exception:
            return None

    def get_attr(self, root, path, attr):
        try:
            return root.find(path).get(attr)
        except Exception:
            return None

    def get_novel_full_metadata(self):
        return self.get_encrypted_map(f"action=book&do=meta&aid={self.aid}&t=1")

    def get_novel_full_description(self):
        return self.get_encrypted_map(f"action=book&do=intro&aid={self.aid}&t=1")

    def get_image(self):
        r = requests.get(
            self.web_url.format(self.aid),
            headers=self.headers,
            verify=False,
        )
        r.encoding = "gbk"
        html = r.text
        if (
            "错误原因：对不起，该文章不存在！" in html
            or "错误原因：对不起，该文章不存在或已被删除！" in html
        ):
            raise ValueError("")
        try:
            soup = bs4(html, "lxml")
            content = soup.find("div", id="content")
            img_tag = content.find("img")
            img = img_tag["src"] if img_tag else None
        except:
            img = None

        return img

    def psot(self, type: TYPE):
        data = {
            Novel.TYPE.METADATA: self.get_novel_full_metadata,
            Novel.TYPE.DESCRIPTION: self.get_novel_full_description,
        }

        if type in data:
            return requests.post(
                self.base_url,
                data=data[type](),
                headers=self.headers,
            )

    def to_dict(self):
        metadata = self.psot(Novel.TYPE.METADATA)
        if (
            "錯誤原因：對不起，該文章不存在！" in metadata.text
            or "錯誤原因：對不起，該文章不存在或已被刪除！" in metadata.text
        ):
            raise ValueError("")

        root = ET.fromstring(metadata.text)
        title = self.get_text(root, "data[@name='Title']")
        author = self.get_attr(root, "data[@name='Author']", "value")
        publish = self.get_attr(root, "data[@name='PressId']", "value")
        thumbnail = self.get_image()
        status = self.get_attr(root, "data[@name='BookStatus']", "value")
        length = self.get_attr(root, "data[@name='BookLength']", "value")
        last_update = self.get_attr(root, "data[@name='LastUpdate']", "value")
        last_section = self.get_text(root, "data[@name='LatestSection']")
        raw_tags = self.get_attr(root, "data[@name='Tags']", "value")
        tags = raw_tags.split() if raw_tags else []
        description = self.psot(Novel.TYPE.DESCRIPTION)

        return {
            "aid": self.aid,
            "title": cc.convert(title) if title else None,
            "author": cc.convert(author) if author else None,
            "publish": cc.convert(publish) if publish else None,
            "thumbnail": thumbnail,
            "status": cc.convert(status) if status else None,
            "length": length,
            "last_update": last_update,
            "last_section": cc.convert(last_section) if last_section else None,
            "tags": [cc.convert(tag) for tag in tags] if tags else [],
            "description": cc.convert(description.text.strip())
            if description
            else None,
        }


def worker(aid):
    try:
        return Novel(aid).to_dict()
    except ValueError:
        return None
    except Exception as e:
        print(f"Error on {aid} {e}")


def main():
    with Pool() as p:
        results = p.map(worker, range(1, 9999))
    results = [r for r in results if r is not None]
    results.sort(key=lambda x: x["aid"])

    with open("novel.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    today = datetime.date.today()
    start = time.time()
    main()
    duration = time.time() - start
    print(f"{today} Finish Update in {duration:.2f}s")
