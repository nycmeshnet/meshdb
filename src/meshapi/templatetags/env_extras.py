# https://stackoverflow.com/a/62798100
import os

from django import template

register = template.Library()


@register.simple_tag
def get_env_var(key):
    return os.environ.get(key)
