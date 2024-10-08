import html
import json
import os

from hobune.channels import is_full_channel
from hobune.comments import getCommentsHTML
from hobune.logger import logger
from hobune.util import generate_meta_tags, quote_url, no_traverse


def generate_download_button(name, url, prefix="/dl"):
    full_url = quote_url(f"{prefix}{url}")
    return f"""
    <a href="{full_url}">
        <div class="button download">
            <i class="icon download"></i> {html.escape(name)}
        </div>
    </a>
    <br>
    """


def create_video_pages(config, channels, templates, html_ext):
    dir_listings = {}
    for channel in channels:
        logger.debug(f"Creating video pages for {channels[channel].name}")
        for video_entry in channels[channel].videos:
            root = video_entry["root"]
            file = video_entry["file"]
            base = file[:-len(".info.json")]
            if root not in dir_listings:
                dir_listings[root] = os.listdir(root)
            files = dir_listings[root]
            try:
                with open(os.path.join(root, file), "r") as f:
                    v = json.load(f)
                page_meta = generate_meta_tags(
                    {
                        "description": v['description'][:256],
                        "author": v['uploader']
                    }
                )
                # Generate comments
                comments_html, comments_count = getCommentsHTML(html.escape(v['title']), v['id'])
                comments_link = ""
                if comments_html:
                    with open(os.path.join(config.output_path, f"comments/{no_traverse(v['id'])}.html"), "w") as f:
                        f.write(templates["base"].format(title=html.escape(v['title'] + ' - Comments'), meta=page_meta,
                                                         content=comments_html))
                    comments_link = f'<p class="comments"><a href="/comments/{v["id"]}{html_ext}">View comments ({comments_count})</a></p>'
                # Set mp4 path
                mp4path = f"{os.path.join(config.files_web_path + root[len(config.files_path):], base)}.mp4"
                for ext in ["mp4", "webm", "mkv"]:
                    if f"{base}.{ext}" in files:
                        mp4path = f"{os.path.join(config.files_web_path + root[len(config.files_path):], base)}.{ext}"
                        break

                # Get thumbnail path
                thumbnail = "/default.png"
                for ext in ["webp", "jpg", "png"]:
                    if (thumbnail_file := f"{base}.{ext}") in files:
                        thumbnail = config.files_web_path + (os.path.join(root, thumbnail_file))[
                                                            len(config.files_path):]

                # Create a download button for the video
                download_buttons_html = generate_download_button("Download video", mp4path)

                # Create multiple video download buttons if we have multiple formats
                for ext in ["webm", "mkv"]:
                    if (alt_file := f"{base}.{ext}") in files:
                        alt_file_url = config.files_web_path + (os.path.join(root, alt_file))[len(config.files_path):]
                        download_buttons_html = generate_download_button("Download mp4", mp4path) + \
                                                generate_download_button(f"Download {ext}", alt_file_url)

                # Description download
                if (desc_file := f"{base}.description") in files:
                    desc_file_url = config.files_web_path + os.path.join(root, desc_file)[len(config.files_path):]
                    download_buttons_html += generate_download_button("Description", desc_file_url)

                # Thumbnail download
                if thumbnail != "/default.png":
                    download_buttons_html += generate_download_button("Thumbnail", thumbnail)

                # Subtitles download
                for vtt in (vtt for vtt in files if vtt.endswith(".vtt")):
                    if vtt.startswith(base):
                        vtt_url = os.path.join(config.files_web_path + root[len(config.files_path):], vtt)
                        vtt_tag = vtt[len(base) + 1:-len('.vtt')]
                        download_buttons_html += generate_download_button(f"Subtitles ({vtt_tag})", vtt_url)

                #Live chat download
                for ext in ["7z", "zip"]:
                    for file in files:
                        if "live_chat" in file and file.endswith(ext) and file.startswith(base):
                            live_chat_url = config.files_web_path + (os.path.join(root, file))[len(config.files_path):]
                            download_buttons_html += generate_download_button("Live Chat", live_chat_url)
                
                # Audio only
                for ext in ["m4a", "mka", "ogg"]:
                    if (audio_file := f"{base}.{ext}") in files:
                        audio_file_url = config.files_web_path + os.path.join(root, audio_file)[len(config.files_path):]
                        download_buttons_html += generate_download_button(f"Audio Only ({ext})", audio_file_url)

                # Subtitles download
                for vtt in (vtt for vtt in files if vtt.endswith(".vtt")):
                    if vtt.startswith(base):
                        vtt_url = os.path.join(config.files_web_path + root[len(config.files_path):], vtt)
                        vtt_tag = vtt[len(base) + 1:-len('.vtt')]
                        download_buttons_html += generate_download_button(f"Subtitles ({vtt_tag})", vtt_url)

                for srt in (srt for srt in files if srt.endswith(".srt")):
                    if srt.startswith(base):
                        srt_url = os.path.join(config.files_web_path + root[len(config.files_path):], srt)
                        #srt_tag = vtt[len(base) + 1:-len('.srt')]
                        download_buttons_html += generate_download_button(f"Subtitles (AI-Generated)", srt_url)

                #Info.json download
                if (info_file := f"{base}.info.json") in files:
                    info_file_url = config.files_web_path + os.path.join(root, info_file)[len(config.files_path):]
                    download_buttons_html += generate_download_button("Info JSON", info_file_url)

                #Torrent download
                if (torrent_file := f"{base}.torrent") in files:
                    torrent_url = config.files_web_path + os.path.join(root, torrent_file)[len(config.files_path):]
                    download_buttons_html += generate_download_button("Torrent", torrent_url)

                
                # Create HTML
                page_html = templates["video"].format(
                    title=html.escape(v['title']),
                    ytlink=f"<a class=\"ytlink\" href=https://www.youtube.com/watch?v={html.escape(v['id'])}>YT</a>",
                    description=html.escape(v['description']).replace('\n', '<br>'),
                    views=v['view_count'],
                    uploader_url=f"{config.web_root}channels/{html.escape(v.get('channel_id', v.get('uploader_id')))}{html_ext}" if is_full_channel(root) else f'{config.web_root}channels/other{html_ext}',
                    uploader_id={html.escape(v.get('channel_id', v.get('uploader_id')))},
                    uploader=html.escape(v['uploader']),
                    date=f"{v['upload_date'][:4]}-{v['upload_date'][4:6]}-{v['upload_date'][6:]}",
                    video=quote_url(mp4path),
                    thumbnail=quote_url(thumbnail),
                    download=download_buttons_html,
                    comments=comments_link
                )

                with open(os.path.join(config.output_path, f"videos/{no_traverse(v['id'])}.html"), "w") as f:
                    f.write(templates["base"].format(title=html.escape(v['title']), meta=page_meta, content=page_html))
            except Exception as e:
                logger.error(f"Error processing {file}")
                print(e)
