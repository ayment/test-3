import os
import io
import fitz
import pytesseract
from PIL import Image
from deep_translator import GoogleTranslator

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

translator = GoogleTranslator(source="en", target="ar")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a PDF and I will translate each page from English → Arabic."
    )


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Processing your PDF... ")

    tg_file = await update.message.document.get_file()
    input_path = "input.pdf"
    await tg_file.download_to_drive(input_path)

    pdf = fitz.open(input_path)

    for i in range(pdf.page_count):
        page = pdf[i]

        text = page.get_text("text").strip()
        ocr_text = ""
        images = page.get_images(full=True)

        for img in images:
            xref = img[0]
            base_img = pdf.extract_image(xref)
            img_bytes = base_img["image"]
            pil_img = Image.open(io.BytesIO(img_bytes))
            ocr_text += pytesseract.image_to_string(pil_img, lang="eng") + "\n"

        full_english = (text + "\n" + ocr_text).strip() or "(No English text found)"
        arabic = translator.translate(full_english)

        new_page = pdf.new_page(i + 1)
        content = (
            f"--- Original English ---\n{full_english}\n\n"
            f"--- Arabic Translation ---\n{arabic}"
        )
        new_page.insert_text((40, 40), content, fontsize=12)

    output_path = "translated.pdf"
    pdf.save(output_path)
    pdf.close()

    await update.message.reply_document(document=open(output_path, "rb"))


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )


if __name__ == "__main__":
    main()
