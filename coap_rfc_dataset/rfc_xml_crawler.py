#!/usr/bin/env python3
# -*- coding:utf-8 -*-


import os
import json
import re
import time
import requests

from tqdm import tqdm



RFC_LIST = [
    7252,
    7641,
    7959,
    8132,
    8323,
    8613,
    8768,
    8974,
    9175,
    9177
]


BASE_URL = (
    "https://www.rfc-editor.org/rfc"
)


OUTPUT_DIR="rfc_dataset"



HEADERS={
    "User-Agent":
    "CoAP-MITL-Research"
}



def download(url):

    for i in range(5):

        try:

            print(
                "GET:",
                url
            )


            r=requests.get(
                url,
                headers=HEADERS,
                timeout=60
            )


            r.raise_for_status()

            return r.text


        except Exception as e:

            print(
                "retry",
                i+1,
                e
            )

            time.sleep(3)


    raise Exception(url)





def save(path,data):

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(data)





def parse_sections(txt):

    sections=[]

    current={
        "title":"ROOT",
        "content":[]
    }


    for line in txt.splitlines():


        # RFC section

        if re.match(
            r"^\d+(\.\d+)*\.\s+",
            line
        ):

            sections.append(
                current
            )

            current={
                "title":
                line.strip(),

                "content":[]
            }


        else:

            current["content"].append(
                line
            )



    sections.append(
        current
    )


    return sections






def extract_requirements(sections):


    results=[]


    keywords=[
        " MUST ",
        " MUST NOT ",
        " SHOULD ",
        " SHOULD NOT ",
        " MAY "
    ]


    for sec in sections:


        text="\n".join(
            sec["content"]
        )


        sentences=text.split(".")


        for s in sentences:

            upper=" "+s.upper()+" "


            for k in keywords:


                if k in upper:

                    results.append(
                        {
                        "section":
                        sec["title"],

                        "keyword":
                        k.strip(),

                        "text":
                        s.strip()
                        }
                    )

                    break


    return results






def process(rfc):


    folder=os.path.join(
        OUTPUT_DIR,
        f"rfc{rfc}"
    )


    os.makedirs(
        folder,
        exist_ok=True
    )


    url=(
        f"{BASE_URL}/rfc{rfc}.txt"
    )


    txt=download(
        url
    )


    save(
        os.path.join(
            folder,
            f"rfc{rfc}.txt"
        ),
        txt
    )


    sections=parse_sections(
        txt
    )


    with open(
        os.path.join(
            folder,
            "sections.json"
        ),
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            sections,
            f,
            indent=2,
            ensure_ascii=False
        )


    req=extract_requirements(
        sections
    )


    with open(
        os.path.join(
            folder,
            "requirements.json"
        ),
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            req,
            f,
            indent=2,
            ensure_ascii=False
        )



    print(
        "DONE RFC",
        rfc
    )






def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


    for rfc in tqdm(
        RFC_LIST
    ):

        try:

            process(
                rfc
            )

        except Exception as e:

            print(
                "FAILED",
                rfc,
                e
            )



if __name__=="__main__":

    main()