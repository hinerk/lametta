# Lametta

Lametta is a configuration management according to my requirements. Its name is inspired by 
"Confetti" - arguably the coolest configuration management system so far - at least by
name - haven't tried it, though. You might notice the lexical gap between "Confetti" and
"Lametta": "Lametta" is German for tinsel, which is plastic garbage you throw on your Christmas
tree to make it look better. Like confetti, you are basically polluting the landscape for 
selfish reasons. But making it from plastic makes it is even worse than confetti. And this is
exactly the spirit I am aiming for: something worse than confetti, built for purely selfish
reasons. Enjoy like there is no tomorrow!

# Idea

I want to be able to define a configuration structure and validate a loaded configuration.
I need no ambiguity. There should only be one legitimate way to express a configuration.
No necessity to coerce a `"1.5"` to float. Even if I expect a float, providing a string
containing the representation of a float value is nothing you should do in a configuration
file. Hell no, this ain't JavaScript.

However, I want to allow for a limited set of legitimate data structures. Consider some
application which would cache stuff in a MongoDB or alternatively write stuff to some folder
(do not judge me - I try to come up with some example - far removed from what could be
considered giving price company secrets). So using MongoDB, the app might require a
configuration section like:

```toml
[backend]
type = "mongodb"
collection = "foo"
database = "bar"
```

While if using a file based backend, it might be configured like:

```toml
[backend]
type = "filesystem"
root = "/home/your/rear"
```

As this is an either-or situation ... fuck it. I do not want to explain my self. This is
how I address this situation:

```python
from lametta import settings
from pathlib import Path


@settings(discriminator_field=("type", "filesystem"))
class FilesystemBackendSettings:
    root: Path


@settings(discriminator_field=("type", "mongodb"))
class MongoDBBackendSettings:
    database: str
    collection: str


@settings
class Settings:
    foo: str = "bar"
    backend: MongoDBBackendSettings | FilesystemBackendSettings
```

So, the `settings` decorator is a bit like a lesser version of `dataclass`. It patches
some functionality into the class such that it can be initialized with a mapping like:
`Setting(**json.load("path_to_my_config.json"))`.
It'll check that each specified field is present in the mapping and that the data type
is matching its declaration[^1]. The conditional branching between both legit backend
configurations is expressed by the union type annotation. This is the only fancy type 
annotation I support. The field which is considered to decide to which data type a
sub-segment is cast as, is specified via the `@settings` decorator on the embedded
structure.

[^1]: obviously I am not smart enough to deal with complex generic stuff or TypeVar and such.
      So you limited to non-generic types except `list[x]` and `tuple[x, y, ...]`. Notable:
      by generic, I mean everything inside square brackets.