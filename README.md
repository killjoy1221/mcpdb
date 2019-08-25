# mcpdb

A database for mcp accessible via REST

## API Usage

### Authentication

TODO

### Get Mapping
`GET /api/<type>/<version>/<srg>`

#### Request Variables

| variable | where | description |
| --- | --- | --- |
| version | path | The minecraft version. Released versions of mcp_config are supported. |
| type | path | The type of request. One of (`class`, `method`, `field`, `param`). |
| srg | path | The srg name of the item to get. |


#### Json Response

|  field  |  type  |      description      |
| ------- | ------ | --------------------- |
| version | string | The minecraft version |
| obf     | string | The obfuscated name   |
| name    | string | The mapped name       |

**method, field, param** have additional properties

|  field  |  type   |        description       |
| ------- | ------- | ------------------------ |
| srg     | string  | The srg name             |
| locked  | boolean | False if anyone can edit |

#### Errors

| error | reason |
| ----- | ------ |
| 404 Not Found | When the requested name does not exist.|

### Set Mapping
`PUT /api/<type>/<version>/<srg>`

#### Request Variables

| variable | where | description |
| --- | --- | --- |
| version | path | The minecraft version. Released versions of mcp_config are supported. |
| type | path | The type of request. One of (`method`, `field`, `param`). |
| srg | path | The srg name of the item to set. |
| name | json | The mcp name to set the entry to. |
| force | json | When true, allows admins to force name changes on locked names. |

#### Json Response

| field | type | description |
| ----- | ---- | ----------- |
| changed | boolean | True if the entry was changed.
| old_name | string | The old name the entry was set to, if any. |

#### Errors

| error | reason |
| ----- | ------ |
| 400 Bad Request | When the user provides incomplete input |
| 403 Forbidden | When a non-admin tries to set a locked name or use the force option. |
| 404 Not Found | When the requested name does not exist |

### Get History
`GET /api/<type>/<version>/<srg>/history`

#### Request Variables

| variable | where | description |
| --- | --- | --- |
| version | path | The minecraft version. Released versions of mcp_config are supported. |
| type | path | The type of request. One of (`method`, `field`, `param`). |
| srg | path | The srg name of the item to get. |

#### Json Array Response

|  field  |  type  |      description      |
| ------- | ------ | --------------------- |
| version | string | The minecraft version |
| srg     | string | The srg name          |
| name    | string | The mapped name       |
| changed_by | string | The username who made this change. |
| created | datetime | The datetime when this change was made. |

#### Errors

| error | reason |
| ----- | ------ |
| 404 Not Found | When the requested name does not exist.|

