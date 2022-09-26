import os
from io import BytesIO

import discord
import pyppeteer
from PIL import Image


class Html2img:
    @classmethod
    async def browser_init(cls):
        """Initializes the browser"""
        cls.browser = await pyppeteer.launch(headless=True, args=["--no-sandbox"])

    tempPNGPath = ".\\html2img\\temp\\temp.png"

    cssPathTable = "\\html2img\\css\\table\\"

    @classmethod
    async def render(cls, html: str, css_path: str):
        """Renders the html and saves it as a png"""
        path = os.getcwd() + css_path + "temp\\index.html"

        page = await cls.browser.newPage()

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        await page.goto("file://" + path)
        os.remove(path)

        size = await page.evaluate(
            """() => {
                const table = document.querySelector('table');
                return [table.offsetWidth, table.offsetHeight];
            }"""
        )
        await page.setViewport({"width": size[0], "height": size[1]})
        await page.screenshot({"path": cls.tempPNGPath})

    @classmethod
    async def html2discord_file(cls, html: str, css: str, file_name: str = "table.png") -> discord.File:
        """Returns a discord file of the rendered html image"""
        await cls.render(html, css)

        img = Image.open(cls.tempPNGPath)
        binaryImg = BytesIO()
        img.save(binaryImg, "PNG")
        os.remove(cls.tempPNGPath)
        binaryImg.seek(0)

        return discord.File(fp=binaryImg, filename=file_name)