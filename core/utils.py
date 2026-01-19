import re
import os
import sys
import inspect
import logging
import copy
import json
import colored
import requests
import magicattr
from math import gcd
from functools import lru_cache
from decimal import Decimal
from datetime import timedelta, datetime
from contextlib import contextmanager

from django.utils import timezone
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.template.defaultfilters import slugify  # Used by other imports

logger = logging.getLogger(__name__)
NBSP = "\u00a0"


def flatten(lst):
    return [item for sublist in lst for item in sublist]


def enum(**kwargs):

    class Enum(tuple):
        def __contains__(self, item):
            for value, display in self:
                if value == item:
                    return True
            return False

        def keys(self):
            return self._keys

        def values(self):
            return tuple(value for value, display in self)

        def displays(self):
            return tuple(display for value, display in self)

        def items(self):
            return tuple((value, display) for value, display in self)

        def keys_displays(self):
            return list(zip(self._keys, self.displays()))

        def find_key_from_value(self, item, default=None):
            for i, (value, display) in enumerate(self):
                if item == value:
                    return self._keys[i]
            return default

    get_value = lambda key, x: x[0] if isinstance(x, tuple) else key
    get_display = lambda x: x[1] if isinstance(x, tuple) else x

    res = Enum((get_value(key, x), get_display(x)) for key, x in kwargs.items())
    for key, x in kwargs.items():
        setattr(res, key, get_value(key, x))
        setattr(res, "%s_display" % key, get_display(x))
    res._keys = tuple(kwargs.keys())
    return res


def deep_getattr(obj, attrs, default=None):
    try:
        return magicattr.get(obj, attrs)
    except (AttributeError, KeyError):
        return default


def deep_update(a: dict, b: dict, path=[], inplace=True, ignore_conflicts=True):
    containers = (list, tuple, dict)

    def deep_update_rec(a, b, path):
        if issubclass(type(a), (list, tuple)) and issubclass(type(b), (list, tuple)):
            a = list(a)
            for i, elt in enumerate(b):
                a[i] = deep_update_rec(a[i], b[i], path=path + [str(i)])
            return a
        if issubclass(type(a), dict) and issubclass(type(b), dict):
            for key in b:
                if key in a:
                    a[key] = deep_update_rec(a[key], b[key], path=path + [str(key)])
                else:
                    # New value in a
                    a[key] = copy.deepcopy(b[key])
            return a
        elif not ignore_conflicts and (issubclass(type(a), containers) or issubclass(type(b), containers)):
            raise ValueError("Structure conflict at " + ".".join(path))
        else:
            # Overwriting value from a with b
            return copy.deepcopy(b)

    if not inplace:
        a = copy.deepcopy(a)
    return deep_update_rec(a, b, path=[])


def partition(iterable, predicate):
    true_items = []
    false_items = []
    for item in iterable:
        if predicate(item):
            true_items.append(item)
        else:
            false_items.append(item)
    return true_items, false_items


def path_join(*args, trailing_slash=False):
    root = args[0]
    if root and root[-1] != "/":
        root += "/"
    path = root + "/".join(str(a).strip("/ ") for a in args[1:] if str(a).strip("/ "))
    if path and path[-1] != "/" and trailing_slash:
        return path + "/"
    return path


def flush(text):
    sys.stdout.write(text)
    sys.stdout.flush()


def progress(text, num, step, color=None):
    if not num % step:
        flush(colored.stylize(text, color) if color else text)


class Colors:
    # Basic colors
    red = colored.fg("red")
    yellow = colored.fg("yellow")
    green = colored.fg("green")
    blue = colored.fg("blue")
    purple = violet = colored.fg("violet")
    dark_gray = colored.fg("dark_gray")
    gray_53 = colored.fg("grey_53")
    light_gray = colored.fg("light_gray")
    # Text
    bold = colored.attr("bold")
    # Generics
    error = bold + red
    warning = bold + yellow
    success = bold + green
    info = bold + blue
    # Reset
    reset = colored.Style.reset


def titleize(title, separator="-", width=70):
    title = f" {title.strip()} "
    separator_width = width - len(title)
    nb_left_separators = (separator_width // 2) // len(separator)
    nb_right_separators = (separator_width - nb_left_separators * len(separator)) // len(separator)
    return separator * nb_left_separators + title + separator * nb_right_separators


@lru_cache(maxsize=None)
def first_domain():
    from django.contrib.sites.models import Site

    return Site.objects.first().domain


def canonical_url(path, request=None, domain=None, scheme=None):
    from django.conf import settings

    if domain is None:
        if request:
            domain = request.get_host()
        else:
            domain = first_domain()
    if scheme is None:
        if request and request.is_secure():
            scheme = "https"
        elif settings.SERVER_STAGE not in ["TEST", "DEV"]:
            # HTTP forbidden in PROD/STAGING
            scheme = "https"
        else:
            scheme = "http"
    return path_join(f"{scheme}://{domain}", path)


def canonical_url_static(path):
    from django.conf import settings
    from django.templatetags.static import static

    url = static(path)
    if settings.USE_LOCAL_STATIC:
        # Add the local domain to force absolute URLS
        return canonical_url(url)
    else:
        return url


def format_price(price):
    """Serialize float price to string as if it was a decimal"""
    return "%.2f" % price if price is not None else None


def strftimedelta(delta, format=None, ignore_zeros=None):
    if delta is None:
        return ""
    ignore_zeros = ignore_zeros if ignore_zeros is not None else bool(format is None)
    res = format if format is not None else r"%d%H%M%S%f"
    # Extract microseconds
    if ignore_zeros is False or delta.microseconds != 0:
        micro = f"{delta.microseconds:06}" if not ignore_zeros else f"{delta.microseconds}µ"
        res = re.sub(r"%f", micro, res)
        milli = f"{delta.microseconds // 1000}ms"
        if delta < timedelta(microseconds=1000):
            milli = "< 1ms"
        res = re.sub(r"%m", milli, res)
    else:
        res = re.sub(r"%m", "", res)
        res = re.sub(r"%f", "", res)
    # Truncate to int
    remainder = int(delta.total_seconds())
    periods = [
        (r"%d", r"{:d}", 60 * 60 * 24),
        (r"%H", r"{:02d}", 60 * 60),
        (r"%M", r"{:02d}", 60),
        (r"%S", r"{:02d}", 1),
    ]
    # Replace
    for pattern, replacement, period_seconds in periods:
        quotient, remainder = divmod(remainder, period_seconds)
        if ignore_zeros:
            replacement = r"{:d}" + pattern[1].lower() + " " if quotient != 0 else ""
        res = re.sub(pattern, replacement.format(quotient), res)
    if ignore_zeros:
        res = "0µ" if not res else res.strip()
    return res


@contextmanager
def warn_if_last_more_than(caller=None, tag=None, log_level=logging.WARNING, **kwargs):
    now = timezone.now()
    timeout = timedelta(**kwargs)
    yield
    time_elapsed = timezone.now() - now
    if time_elapsed <= timeout:
        return
    if not caller:
        ignored_functions = "__exit__", "inner", "warn_if_last_more_than"
        parents = [x.function for x in inspect.stack()]
        caller = next(filter(lambda x: x not in ignored_functions, parents))
    if tag:
        caller += "#" + tag
    result = strftimedelta(time_elapsed)
    expected = strftimedelta(timeout)
    # Warning: {caller} is replaced before logging to ensure coherent grouping, other arguments are replaced after logging
    logger.log(log_level, f"{caller} took too long: %s > %s", result, expected, exc_info=True)


def timestamp(dt):
    if not dt:
        return None
    return int(datetime.timestamp(dt))


def jdumps(d, prompt="", indent=2, starting_indent=0, newline=False):
    """
    Convert a python object into a string using json.dumps and a custom formatting.
    """
    prompt += " " * indent * starting_indent
    res = f"\n{prompt}" if newline else prompt
    # Dumping in json and adding prompt
    res += json.dumps(d, indent=indent).replace("\n", f"\n{prompt}")
    return res


def display_price(price, currency=None, symbol=None):
    if price is None:
        return ""
    assert isinstance(price, Decimal), "Invalid price type %s" % type(price)
    symbol = symbol or (currency and currency.symbol) or "€"
    return f"{price:.2f}{NBSP}{symbol}"


def display_percent(percent, symbol="%"):
    if percent is None:
        return ""
    return f"{Decimal(percent):.2f}{NBSP}{symbol}"


def cast(input, output_type, default=None):
    """
    Example:
        cast("42", int, None) ==> 42
        cast("plop", int, None) ==> None (No error)
    """
    try:
        return output_type(input)
    except (ValueError, TypeError):
        return default


@lru_cache(maxsize=None)
def get_server_ip():
    """
    See: https://www.ipify.org/
    """
    from django.conf import settings

    if settings.SERVER_STAGE == "TEST":
        return "127.0.0.1"
    ip = requests.get("https://api.ipify.org").text
    return ip


def get_client_ip(request, private_ips_prefix=None):
    """
    Return the client public ip from a request
    """
    ip = request.META.get("REMOTE_ADDR")
    # Try to get the first non-proxy ip (not a private ip) from the HTTP_X_FORWARDED_FOR
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        proxies = x_forwarded_for.split(",")
        if private_ips_prefix:
            # Remove the private ips from the beginning
            while len(proxies) > 0 and proxies[0].startswith(private_ips_prefix):
                proxies.pop(0)
        # Take the first ip which is not a private one (of a proxy)
        if len(proxies) > 0:
            ip = proxies[0].strip()
    # Possibly None ip
    return ip


def dict_to_named_tuple(d: dict, tuple_name: str):
    from collections import namedtuple

    NT = namedtuple(tuple_name, d)
    return NT(**d)


def style(message, color):
    from django.conf import settings  # Forbidden in core.utils root module

    if settings.USE_COLORED_OUTPUT:
        return colored.stylize(message, color)
    return message


def flatten_dict_for_formdata(input_dict, sep="[{i}]"):
    """
    Transform nested json data into form flat dict
    Exemple: "data": [{"key":"value"}] --> "data[0].key": "value"
    See: https://stackoverflow.com/questions/68754458/with-format-multipart-in-test-client-data-of-nested-dict-been-ignored-or-remo
    """

    def __flatten(value, prefix, result_dict, previous):
        if isinstance(value, dict):
            if prefix and previous == "dict":
                prefix += "."

            for key, v in value.items():
                __flatten(v, prefix + key, result_dict, previous="dict")

        elif isinstance(value, (list, tuple)):
            for i, v in enumerate(value):
                __flatten(v, prefix + sep.format(i=i), result_dict, previous="list")
        else:
            result_dict[prefix] = value

        return result_dict

    if not input_dict:
        return ""

    return __flatten(input_dict, "", {}, previous=None)


@contextmanager
def download_file(url, timeout=None):
    """
    Download an external file from the url specified.
    The download is streamed and recorded by chunks in a tmp file.

    TODO: allow storage directly in model
    """
    from core.api.exceptions import InternalError

    response = requests.get(url, timeout=timeout, stream=True)
    if not response.ok:
        raise InternalError("DOWNLOAD_FAILED", details={"url": url, "response": response})
    with NamedTemporaryFile() as tmp:
        for chunk in response.iter_content(chunk_size=1024 * 8):
            if not chunk:
                break
            tmp.write(chunk)

        tmp.seek(0)
        yield File(tmp)


class LCG:
    """
    Linear Congruential Generator (LCG). This is a random integer number generator with the following properties:
    - Exhaustive cycle: all numbers in the interval are generated 1 time before repetition
    - Pseudo random: number seems random but are deterministically generated from a seed
    - Memory efficient: do not consume memory other than stored parameters
    """

    def __init__(self, interval_start, interval_end, multiplier, increment, seed):
        """
        Initialize the LCG.
        :param start: Lower bound of the interval (inclusive).
        :param end: Upper bound of the interval (exclusive).
        :param multiplier: The multiplier (a) for the LCG formula.
        :param increment: The increment (c) for the LCG formula.
        :param seed: The starting point for the generator, must be within the interval.
        """
        self.start = interval_start
        self.end = interval_end
        self.range_size = self.end - self.start
        self.multiplier = multiplier
        self.increment = increment
        self.modulus = self.range_size
        self.state = seed - self.start
        self.validate_parameters(self.start, self.end, self.modulus, multiplier, increment, seed)

    def next(self):
        """
        Generate the next number in the sequence.
        :return: The next number within the specified interval.
        """
        self.state = (self.multiplier * self.state + self.increment) % self.modulus
        return self.state + self.start

    @classmethod
    def validate_parameters(cls, start, end, modulus, multiplier, increment, seed):
        """
        Validates whether the given LCG parameters produce a full cycle.
        :param modulus: The size of the interval.
        :param multiplier: The multiplier (a).
        :param increment: The increment (c).
        :return: True if parameters are valid, otherwise raises a ValueError.
        """
        if not start <= seed < end:
            raise ValueError("Seed must be within the specified interval.")
        if gcd(multiplier, modulus) != 1:
            raise ValueError("Multiplier (a) and modulus (m) must be coprime.")
        for prime_factor in cls.prime_factors(modulus):
            if (multiplier - 1) % prime_factor != 0:
                raise ValueError(f"Multiplier (a) - 1 must be divisible by {prime_factor} (prime factor of modulus).")
        if gcd(increment, modulus) != 1:
            raise ValueError("Increment (c) and modulus (m) must be coprime.")

    @classmethod
    def prime_factors(cls, n):
        """Returns the prime factors of a number n."""
        factors = []
        i = 2
        while i * i <= n:
            while n % i == 0:
                factors.append(i)
                n //= i
            i += 1
        if n > 1:
            factors.append(n)
        return factors


USER_ALLOWED_CHARACTERS = "aAzZ-09 .:,+*'\"()#~/_@"
USER_FORBIDDEN_CHARACTERS = ";|?!`$\r\t\n{}[]<>\\"
USER_FORBIDDEN_CHARACTERS_PATTERN = f"[{re.escape(USER_FORBIDDEN_CHARACTERS)}]"


def validate_user_text_content(value, max_length=None):
    """
    Removes suspicious characters from user's free fields.
    """
    if value in (None, ""):
        return value
    res = re.sub(USER_FORBIDDEN_CHARACTERS_PATTERN, "", value).strip()
    if max_length is not None:
        res = res[:max_length]
    return res.strip()
