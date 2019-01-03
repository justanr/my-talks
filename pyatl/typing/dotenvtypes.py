import typing as t

T = t.TypeVar('T')
KT = t.TypeVar('KT')
VT = t.TypeVar('VT')

ConfigSettings = t.Dict[str, t.Tuple[str, t.Type, t.Optional[t.Any]]]
LoadedConfig = t.Dict[str, t.Any]

def bind_environ_to(c: t.Type[T], environ: t.Dict[str, str]) -> T:
    raw = '\n'.join([f"{k}={v}" for k, v in environ.items()])
    return bind_to(c, raw)

def bind_to(c: t.Type[T], raw: str) -> T:
    settings = load_type_hints_and_defaults(c)
    parsed = parse_config(raw, settings)
    return bind_to_config(c, parsed)


def load_type_hints_and_defaults(c: t.Type[T]) -> ConfigSettings:
    loaded = {}

    for name, hint in t.get_type_hints(c).items():
        default = getattr(c, name, None)
        loaded[name.lower()] = (name, hint, default)

    return loaded


def bind_to_config(c: t.Type[T], loaded: LoadedConfig) -> T:
    config = c()

    for name, value in loaded.items():
        setattr(config, name, value)

    return config


def parse_config(raw: str, settings: ConfigSettings) -> LoadedConfig:
    cb = ConfigBinder()
    config: LoadedConfig = {}
    lines = raw.split('\n')

    for (name, _, default) in settings.values():
        config[name] = default

    for line in lines:
        name, value = line.split('=', 1)

        actual = settings.get(name.lower(), None)

        if actual is None:
            continue

        try:
            config[actual[0]] = cb.cast(value, actual[1])
        except Exception as e:
            if actual[2] is not None:
                config[actual[0]] = actual[2]
            raise Exception(f"Could not parse {name} from {value}") from e

    return config

class ConfigBinder:
    def __init__(self):
        self.kinds = {
            str: self.as_str,
            float: self.as_float,
            int: self.as_int,
            t.List: self.as_list,
            t.Set: self.as_set,
            t.Dict: self.as_dict
        }

    def as_int(self, in_: str) -> int:
        return int(in_)

    def as_float(self, in_: str) -> float:
        return float(in_)

    def as_str(self, in_: str) -> str:
        return in_

    def as_list(self, in_: str, sub: t.Type[T] = str) -> t.List[T]:
        values = in_.split(',')
        return [self.cast(v, sub) for v in values]

    def as_dict(self, in_: str, kt: t.Type[KT] = str, vt: t.Type[VT] = str) -> t.Dict[KT, VT]:
        dct = {}
        for pair in in_.split(','):
            key, value = pair.split('=')
            dct[self.cast(key, kt)] = self.cast(value, vt)

        return dct

    def as_set(self, in_: str, sub: t.Type[T] = str) -> t.Set[T]:
        return set(self.cast(v, sub) for v in in_.split(','))

    def cast(self, in_: str, as_: t.Type[T]) -> T:
        subtypes = getattr(as_, '__args__', [])

        if subtypes:
            as_ = as_.__origin__
            return self.kinds[as_](in_, *subtypes)

        return self.kinds[as_](in_)
