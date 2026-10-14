# -*- coding: utf-8 -*-


import datetime


COLORS = {'green':
                {'neutral': (0xbb, 0xff, 0xbb),
                 'bright' : (0x0, 0xff, 0x0),
                },
          'red'  :
                {'neutral': (0xff, 0xbb, 0xbb),
                 'bright' : (0xff, 0x0, 0x0),
                },
         }

PLAIN_COLORS = {'green': '#bbffbb',
                'red'  : '#ffbbbb',
                'yellow': '#ffffbb',
                'violet': '#ff6699',
                'pink': '#bb99bb',
                'white': '#ffffff'}

color_by_status = {'ok': 'green',
                   'error': 'red',
                   'accepted': 'yellow',
                   'ignored': 'violet',
                   'coding_style_violation': 'pink',
                   'none': 'white'}

sign_by_status =  {'ok': '+',
                   'error': '&minus;',
                   'accepted': 'ac',
                   'ignored': 'ignored',
                   'coding_style_violation': 'style'}

def encode_color_to_css(color_tuple):
    return '#{0:02x}{1:02x}{2:02x}'.format(*color_tuple)


def get_submission_color(color_text):
    return PLAIN_COLORS[color_text]
