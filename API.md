
## Motley_Cue API

| Endpoint            | Authentication          | Query Parameters | Description |
|---------------------|-------------------------|------------------|-------------|
|||||
| /                   | -                       | -                | API root; shows available endpoints. |
| /info               | -                       | -                | Service-specific information. |
| /info/authorisation | HTTP Bearer<sup>1</sup> | -                | Authorisation information for specific OP<br>(issuer of given token). |
| /verify_user        | HTTP Bearer<sup>2</sup> | *username*: str  | Verifies if a given token belongs to<br>given local account (*username*). |
|||||
| /user               | -                       | -                | User API root; shows available endpoints. |
| /user/get_status    | HTTP Bearer<sup>2</sup> | -                | Get information about your local account. |
| /user/deploy        | HTTP Bearer<sup>2</sup> | -                | Provision local account. |
| /user/suspend       | HTTP Bearer<sup>2</sup> | -                | Suspend local account. |
|||||
| /admin              | -                       | -                | Admin API root; shows available endpoints. |
| /admin/suspend      | HTTP Bearer<sup>3</sup> | *sub*: str<br>*iss*: str                | Suspends the local account belonging to<br>OIDC user uniquely identified by *sub* and *iss*. |
| /admin/resume       | HTTP Bearer<sup>3</sup> | *sub*: str<br>*iss*: str                | Restores the suspended local account belonging to<br>OIDC user uniquely identified by *sub* and *iss*. |
|||


<sup>1</sup> requires valid access token from a supported OP<br>
<sup>2</sup> requires valid access token of an authorised user<br>
<sup>3</sup> requires valid access token of an authorised user with admin role