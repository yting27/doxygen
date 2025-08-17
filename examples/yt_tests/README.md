## Run command:

```bash
$ROOT/build/bin/doxygen -d sections
```

'prot' - 0 (public)
       - 1 (protected)
       - 2 (private)


Table `compounddef`:
- kind: exclude file/page
- prot: public (for APIs)
- fileid (reference `path`)
- concatenate descriptions

Table `compoundref`:
- Base/derive classes

Table `member`:
- scope_rowid: `compounddef` entry
- memberdef_rowid: `memberdef` entry

Table `memberdef`:
- concatenate descriptions
- name: function definition
- argsstring: argument list
- scope: class/namespace/struct
- type: return type
- prot: access specifier
- static: is static function
- file_id
- kind: function/enumeration

Table `path`:
- name: relative file path from Doxygen file
- local: local library (1), standard library (0)



## Getting Started

```
uv venv --python 3.12.3
uv sync
```