from ipywidgets import Layout, HBox, Button, Textarea


def get_ui():
    btn_start = Button(
        description='Start Crawl',
        button_style='success',
    )

    btn_combine_data = Button(
        description='Combine Data',
        button_style='success',
    )

    text_area_urls = Textarea(
        placeholder='Enter URLs here, 1 per line',
        layout=Layout(overflow_x='scroll',
                      width='auto',
                      height='100px',
                      flex_direction='row',
                      display='flex')
    )

    hbox = HBox([btn_start, btn_combine_data])
    return hbox, text_area_urls
