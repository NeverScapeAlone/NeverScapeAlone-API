# NeverScapeAlone-API Repository

- [NeverScapeAlone-API Repository](#neverscapealone-api-repository)
- [Socket I/O Logic](#socket-io-logic)
    - [Request schema for client -> API](#request-schema-for-client---api)
    - [Request schema for API -> client](#request-schema-for-api---client)
      - [detail](#detail)
      - [SearchMatches](#searchmatches)
      - [MatchData](#matchdata)
      - [PingData](#pingdata)
- [Setting up your environment](#setting-up-your-environment)
    - [INSTALLING NGINX](#installing-nginx)
    - [INSTALLING MYSQL](#installing-mysql)
    - [INSTALLING PHP](#installing-php)
      - [INPUT THE FOLLOWING](#input-the-following)
    - [INSTALLING DOCKER](#installing-docker)
    - [INSTALLING DOCKER-COMPOSE](#installing-docker-compose)
    - [OPENING MYSQL TO THE WORLD](#opening-mysql-to-the-world)
      - [CHANGE BIND ADDRESS TO THIS:](#change-bind-address-to-this)
      - [ENTER YOUR PASSWORD "password" if you didn't change the default](#enter-your-password-password-if-you-didnt-change-the-default)
    - [INSTALLING PHPMYADMIN](#installing-phpmyadmin)
      - [PLACE THIS IN THE phpmyadmin.conf FILE](#place-this-in-the-phpmyadminconf-file)
      - [REPLACE THE OLD FILE WITH THIS](#replace-the-old-file-with-this)
      - [you can now go to http://{youripv4domain}.com/phpmyadmin and login to your mysql database](#you-can-now-go-to-httpyouripv4domaincomphpmyadmin-and-login-to-your-mysql-database)
    - [Entering in the NeverScapeAlone-API mysql files:](#entering-in-the-neverscapealone-api-mysql-files)
    - [INSTALLING REDIS](#installing-redis)
      - [IN THE redis.conf file, change the following lines:](#in-the-redisconf-file-change-the-following-lines)
    - [GITHUB RUNNER](#github-runner)
    - [GITHUB REPOSITORY](#github-repository)

# Socket I/O Logic

Okhttp request object looks like this:

```
Request request = new Request.Builder()
        .url(url)
        .addHeader("User-Agent", RuneLite.USER_AGENT) // RuneLite-38fh3 commit
        .addHeader("Login", username) // "Ferrariic"
        .addHeader("Discord", discord) // base64 encoded! example: QEZlcnJhcmlpYyMwMDAx
        .addHeader("Discord_ID", discord_id) // example: 178965680266149888
        .addHeader("Token", token) // example: y5BAz6OiYaZO-8YpQf_OLUWT6Q3WK-6K
        .addHeader("Time", Instant.now().toString()) // doesn't really matter
        .addHeader("Version", pluginVersionSupplier.get()) // plugin version, ex. v3.0.0-alpha
        .build();
```

1. Connect to "/V#/lobby/{group_identifier}/{passcode}"
The group identifier is the group name, such as `battle-shanty-hooded`
The passcode is a plain-text passcode that would be used for private matches.
Tip: group_identifier = 0 is the default lobby.
Tip: passcode entry does not matter if the lobby is private, you can put anything there.


### Request schema for client -> API

```
{
    "title": "request",
    "description": "incoming request model from the client",
    "type": "object",
    "properties": {
        "detail": {
            "title": "Detail",
            "type": "string"
        },
        "chat_message": {
            "$ref": "#/definitions/chat"
        },
        "like": {
            "title": "Like",
            "type": "integer"
        },
        "dislike": {
            "title": "Dislike",
            "type": "integer"
        },
        "kick": {
            "title": "Kick",
            "type": "integer"
        },
        "promote": {
            "title": "Promote",
            "type": "integer"
        },
        "status": {
            "$ref": "#/definitions/status"
        },
        "location": {
            "$ref": "#/definitions/location"
        },
        "inventory": {
            "title": "Inventory",
            "type": "array",
            "items": {
                "$ref": "#/definitions/inventory_item"
            }
        },
        "stats": {
            "$ref": "#/definitions/stats"
        },
        "prayer": {
            "title": "Prayer",
            "type": "array",
            "items": {
                "$ref": "#/definitions/prayer_slot"
            }
        },
        "equipment": {
            "$ref": "#/definitions/equipment"
        },
        "ping_payload": {
            "$ref": "#/definitions/ping"
        },
        "search": {
            "title": "Search",
            "type": "string"
        },
        "match_list": {
            "title": "Match List",
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "gamestate": {
            "title": "Gamestate",
            "type": "integer"
        },
        "create_match": {
            "$ref": "#/definitions/create_match"
        }
    },
    "required": [
        "detail"
    ],
    "definitions": {
        "chat": {
            "title": "chat",
            "description": "chat model",
            "type": "object",
            "properties": {
                "username": {
                    "title": "Username",
                    "type": "string"
                },
                "message": {
                    "title": "Message",
                    "type": "string"
                },
                "timestamp": {
                    "title": "Timestamp",
                    "type": "integer"
                }
            },
            "required": [
                "message"
            ]
        },
        "status": {
            "title": "status",
            "description": "player status",
            "type": "object",
            "properties": {
                "hp": {
                    "title": "Hp",
                    "type": "integer"
                },
                "base_hp": {
                    "title": "Base Hp",
                    "type": "integer"
                },
                "prayer": {
                    "title": "Prayer",
                    "type": "integer"
                },
                "base_prayer": {
                    "title": "Base Prayer",
                    "type": "integer"
                },
                "run_energy": {
                    "title": "Run Energy",
                    "type": "integer"
                },
                "special_attack": {
                    "title": "Special Attack",
                    "type": "integer"
                }
            },
            "required": [
                "hp",
                "base_hp",
                "prayer",
                "base_prayer",
                "run_energy",
                "special_attack"
            ]
        },
        "location": {
            "title": "location",
            "description": "location model",
            "type": "object",
            "properties": {
                "x": {
                    "title": "X",
                    "type": "integer"
                },
                "y": {
                    "title": "Y",
                    "type": "integer"
                },
                "regionX": {
                    "title": "Regionx",
                    "type": "integer"
                },
                "regionY": {
                    "title": "Regiony",
                    "type": "integer"
                },
                "regionID": {
                    "title": "Regionid",
                    "type": "integer"
                },
                "plane": {
                    "title": "Plane",
                    "type": "integer"
                },
                "world": {
                    "title": "World",
                    "type": "integer"
                }
            },
            "required": [
                "x",
                "y",
                "regionX",
                "regionY",
                "regionID",
                "plane",
                "world"
            ]
        },
        "inventory_item": {
            "title": "inventory_item",
            "description": "inventory_item model",
            "type": "object",
            "properties": {
                "item_id": {
                    "title": "Item Id",
                    "type": "integer"
                },
                "item_amount": {
                    "title": "Item Amount",
                    "type": "integer"
                }
            },
            "required": [
                "item_id",
                "item_amount"
            ]
        },
        "stat_information": {
            "title": "stat_information",
            "type": "object",
            "properties": {
                "boosted": {
                    "title": "Boosted",
                    "type": "integer"
                },
                "real": {
                    "title": "Real",
                    "type": "integer"
                },
                "experience": {
                    "title": "Experience",
                    "type": "integer"
                }
            },
            "required": [
                "boosted",
                "real",
                "experience"
            ]
        },
        "stats": {
            "title": "stats",
            "description": "player skills",
            "type": "object",
            "properties": {
                "Attack": {
                    "$ref": "#/definitions/stat_information"
                },
                "Strength": {
                    "$ref": "#/definitions/stat_information"
                },
                "Defence": {
                    "$ref": "#/definitions/stat_information"
                },
                "Ranged": {
                    "$ref": "#/definitions/stat_information"
                },
                "Prayer": {
                    "$ref": "#/definitions/stat_information"
                },
                "Magic": {
                    "$ref": "#/definitions/stat_information"
                },
                "Runecraft": {
                    "$ref": "#/definitions/stat_information"
                },
                "Construction": {
                    "$ref": "#/definitions/stat_information"
                },
                "Hitpoints": {
                    "$ref": "#/definitions/stat_information"
                },
                "Agility": {
                    "$ref": "#/definitions/stat_information"
                },
                "Herblore": {
                    "$ref": "#/definitions/stat_information"
                },
                "Thieving": {
                    "$ref": "#/definitions/stat_information"
                },
                "Crafting": {
                    "$ref": "#/definitions/stat_information"
                },
                "Fletching": {
                    "$ref": "#/definitions/stat_information"
                },
                "Slayer": {
                    "$ref": "#/definitions/stat_information"
                },
                "Hunter": {
                    "$ref": "#/definitions/stat_information"
                },
                "Mining": {
                    "$ref": "#/definitions/stat_information"
                },
                "Smithing": {
                    "$ref": "#/definitions/stat_information"
                },
                "Fishing": {
                    "$ref": "#/definitions/stat_information"
                },
                "Cooking": {
                    "$ref": "#/definitions/stat_information"
                },
                "Firemaking": {
                    "$ref": "#/definitions/stat_information"
                },
                "Woodcutting": {
                    "$ref": "#/definitions/stat_information"
                },
                "Farming": {
                    "$ref": "#/definitions/stat_information"
                },
                "Overall": {
                    "$ref": "#/definitions/stat_information"
                }
            },
            "required": [
                "Attack",
                "Strength",
                "Defence",
                "Ranged",
                "Prayer",
                "Magic",
                "Runecraft",
                "Construction",
                "Hitpoints",
                "Agility",
                "Herblore",
                "Thieving",
                "Crafting",
                "Fletching",
                "Slayer",
                "Hunter",
                "Mining",
                "Smithing",
                "Fishing",
                "Cooking",
                "Firemaking",
                "Woodcutting",
                "Farming",
                "Overall"
            ]
        },
        "prayer_slot": {
            "title": "prayer_slot",
            "description": "prayer slot",
            "type": "object",
            "properties": {
                "prayer_name": {
                    "title": "Prayer Name",
                    "type": "string"
                },
                "prayer_varbit": {
                    "title": "Prayer Varbit",
                    "type": "integer"
                }
            },
            "required": [
                "prayer_name",
                "prayer_varbit"
            ]
        },
        "equipment_item": {
            "title": "equipment_item",
            "type": "object",
            "properties": {
                "item_id": {
                    "title": "Item Id",
                    "type": "integer"
                },
                "item_amount": {
                    "title": "Item Amount",
                    "type": "integer"
                }
            },
            "required": [
                "item_id"
            ]
        },
        "equipment": {
            "title": "equipment",
            "type": "object",
            "properties": {
                "head": {
                    "$ref": "#/definitions/equipment_item"
                },
                "cape": {
                    "$ref": "#/definitions/equipment_item"
                },
                "amulet": {
                    "$ref": "#/definitions/equipment_item"
                },
                "ammo": {
                    "$ref": "#/definitions/equipment_item"
                },
                "weapon": {
                    "$ref": "#/definitions/equipment_item"
                },
                "body": {
                    "$ref": "#/definitions/equipment_item"
                },
                "shield": {
                    "$ref": "#/definitions/equipment_item"
                },
                "legs": {
                    "$ref": "#/definitions/equipment_item"
                },
                "gloves": {
                    "$ref": "#/definitions/equipment_item"
                },
                "boots": {
                    "$ref": "#/definitions/equipment_item"
                },
                "ring": {
                    "$ref": "#/definitions/equipment_item"
                }
            }
        },
        "ping": {
            "title": "ping",
            "description": "ping model",
            "type": "object",
            "properties": {
                "username": {
                    "title": "Username",
                    "type": "string"
                },
                "x": {
                    "title": "X",
                    "type": "integer"
                },
                "y": {
                    "title": "Y",
                    "type": "integer"
                },
                "regionX": {
                    "title": "Regionx",
                    "type": "integer"
                },
                "regionY": {
                    "title": "Regiony",
                    "type": "integer"
                },
                "regionID": {
                    "title": "Regionid",
                    "type": "integer"
                },
                "plane": {
                    "title": "Plane",
                    "type": "integer"
                },
                "color_r": {
                    "title": "Color R",
                    "type": "integer"
                },
                "color_g": {
                    "title": "Color G",
                    "type": "integer"
                },
                "color_b": {
                    "title": "Color B",
                    "type": "integer"
                },
                "color_alpha": {
                    "title": "Color Alpha",
                    "type": "integer"
                },
                "isAlert": {
                    "title": "Isalert",
                    "type": "boolean"
                }
            },
            "required": [
                "username",
                "x",
                "y",
                "regionX",
                "regionY",
                "regionID",
                "plane",
                "color_r",
                "color_g",
                "color_b",
                "color_alpha",
                "isAlert"
            ]
        },
        "create_match": {
            "title": "create_match",
            "description": "create match payload",
            "type": "object",
            "properties": {
                "activity": {
                    "title": "Activity",
                    "type": "string"
                },
                "party_members": {
                    "title": "Party Members",
                    "type": "string"
                },
                "experience": {
                    "title": "Experience",
                    "type": "string"
                },
                "split_type": {
                    "title": "Split Type",
                    "type": "string"
                },
                "accounts": {
                    "title": "Accounts",
                    "type": "string"
                },
                "regions": {
                    "title": "Regions",
                    "type": "string"
                },
                "RuneGuard": {
                    "title": "Runeguard",
                    "type": "string"
                },
                "notes": {
                    "title": "Notes",
                    "type": "string"
                },
                "group_passcode": {
                    "title": "Group Passcode",
                    "type": "string"
                }
            },
            "required": [
                "activity",
                "party_members",
                "experience",
                "split_type",
                "accounts",
                "regions",
                "RuneGuard",
                "notes",
                "group_passcode"
            ]
        }
    }
}
```

### Request schema for API -> client

```
public class Payload {
    // General information payload
    @SerializedName("detail") // server detail, or subject line. What is the message about?
    ServerStatusCode status;
    @SerializedName("server_message") // server message, is there any flavor text the server is sending as well?
    ServerMessage serverMessage;
    @SerializedName("join") // the group ID to join on a create_match request
    String group_id;
    @SerializedName("passcode") // the passcode that is sent on a create_match request
    String passcode;
    @SerializedName("RuneGuard") // the passcode that is sent on a create_match request
    boolean RuneGuard;
    @SerializedName("search_match_data") // limited data to be sent over to the client, this is mainly for selecting a match
    SearchMatches search;
    @SerializedName("match_data") // data regarding the match itself
    MatchData matchData;
    @SerializedName("ping_data") // incoming ping data
    PingData pingData;
    @SerializedName("chat_data") // incoming ping data
    ChatData chatData;
}
```
#### detail
```
public enum ServerStatusCode {
    @SerializedName("request join new match")
    JOIN_NEW_MATCH,
    @SerializedName("disconnected")
    DISCONNECTED,
    @SerializedName("successful connection")
    SUCCESSFUL_CONNECTION,
    @SerializedName("bad passcode")
    BAD_PASSCODE,
    @SerializedName("match update")
    MATCH_UPDATE,
    @SerializedName("global message")
    GLOBAL_MESSAGE,
    @SerializedName("search match data")
    SEARCH_MATCH_DATA,
    @SerializedName("incoming ping")
    INCOMING_PING,
    @SerializedName("incoming chat")
    INCOMING_CHAT;
}
```

#### SearchMatches
```
{
    "title": "all_search_match_info",
    "type": "object",
    "properties": {
        "search_matches": {
            "title": "Search Matches",
            "type": "array",
            "items": {
                "$ref": "#/definitions/search_match_info"
            }
        }
    },
    "required": [
        "search_matches"
    ],
    "definitions": {
        "search_match_info": {
            "title": "search_match_info",
            "type": "object",
            "properties": {
                "ID": {
                    "title": "Id",
                    "type": "string"
                },
                "activity": {
                    "title": "Activity",
                    "type": "string"
                },
                "party_members": {
                    "title": "Party Members",
                    "type": "string"
                },
                "isPrivate": {
                    "title": "Isprivate",
                    "type": "boolean"
                },
                "RuneGuard": {
                    "title": "Runeguard",
                    "type": "boolean"
                },
                "experience": {
                    "title": "Experience",
                    "type": "string"
                },
                "split_type": {
                    "title": "Split Type",
                    "type": "string"
                },
                "accounts": {
                    "title": "Accounts",
                    "type": "string"
                },
                "regions": {
                    "title": "Regions",
                    "type": "string"
                },
                "player_count": {
                    "title": "Player Count",
                    "type": "string"
                },
                "party_leader": {
                    "title": "Party Leader",
                    "type": "string"
                },
                "match_version": {
                    "title": "Match Version",
                    "type": "string"
                },
                "notes": {
                    "title": "Notes",
                    "type": "string"
                }
            },
            "required": [
                "ID",
                "activity",
                "party_members",
                "isPrivate",
                "RuneGuard",
                "experience",
                "split_type",
                "accounts",
                "regions",
                "player_count",
                "party_leader",
                "match_version"
            ]
        }
    }
}
```

#### MatchData
```
{
    "title": "match",
    "description": "match model",
    "type": "object",
    "properties": {
        "discord_invite": {
            "title": "Discord Invite",
            "type": "string"
        },
        "ID": {
            "title": "Id",
            "type": "string"
        },
        "activity": {
            "title": "Activity",
            "type": "string"
        },
        "party_members": {
            "title": "Party Members",
            "type": "string"
        },
        "group_passcode": {
            "title": "Group Passcode",
            "type": "string"
        },
        "isPrivate": {
            "title": "Isprivate",
            "type": "boolean"
        },
        "RuneGuard": {
            "title": "Runeguard",
            "type": "boolean"
        },
        "match_version": {
            "title": "Match Version",
            "type": "string"
        },
        "notes": {
            "title": "Notes",
            "type": "string"
        },
        "ban_list": {
            "title": "Ban List",
            "type": "array",
            "items": {
                "type": "integer"
            }
        },
        "requirement": {
            "$ref": "#/definitions/requirement"
        },
        "players": {
            "title": "Players",
            "type": "array",
            "items": {
                "$ref": "#/definitions/player"
            }
        }
    },
    "required": [
        "ID",
        "activity",
        "party_members",
        "group_passcode",
        "isPrivate",
        "RuneGuard",
        "match_version",
        "requirement",
        "players"
    ],
    "definitions": {
        "requirement": {
            "title": "requirement",
            "description": "match requirements",
            "type": "object",
            "properties": {
                "experience": {
                    "title": "Experience",
                    "type": "string"
                },
                "split_type": {
                    "title": "Split Type",
                    "type": "string"
                },
                "accounts": {
                    "title": "Accounts",
                    "type": "string"
                },
                "regions": {
                    "title": "Regions",
                    "type": "string"
                }
            },
            "required": [
                "experience",
                "split_type",
                "accounts",
                "regions"
            ]
        },
        "stat_information": {
            "title": "stat_information",
            "type": "object",
            "properties": {
                "boosted": {
                    "title": "Boosted",
                    "type": "integer"
                },
                "real": {
                    "title": "Real",
                    "type": "integer"
                },
                "experience": {
                    "title": "Experience",
                    "type": "integer"
                }
            },
            "required": [
                "boosted",
                "real",
                "experience"
            ]
        },
        "stats": {
            "title": "stats",
            "description": "player skills",
            "type": "object",
            "properties": {
                "Attack": {
                    "$ref": "#/definitions/stat_information"
                },
                "Strength": {
                    "$ref": "#/definitions/stat_information"
                },
                "Defence": {
                    "$ref": "#/definitions/stat_information"
                },
                "Ranged": {
                    "$ref": "#/definitions/stat_information"
                },
                "Prayer": {
                    "$ref": "#/definitions/stat_information"
                },
                "Magic": {
                    "$ref": "#/definitions/stat_information"
                },
                "Runecraft": {
                    "$ref": "#/definitions/stat_information"
                },
                "Construction": {
                    "$ref": "#/definitions/stat_information"
                },
                "Hitpoints": {
                    "$ref": "#/definitions/stat_information"
                },
                "Agility": {
                    "$ref": "#/definitions/stat_information"
                },
                "Herblore": {
                    "$ref": "#/definitions/stat_information"
                },
                "Thieving": {
                    "$ref": "#/definitions/stat_information"
                },
                "Crafting": {
                    "$ref": "#/definitions/stat_information"
                },
                "Fletching": {
                    "$ref": "#/definitions/stat_information"
                },
                "Slayer": {
                    "$ref": "#/definitions/stat_information"
                },
                "Hunter": {
                    "$ref": "#/definitions/stat_information"
                },
                "Mining": {
                    "$ref": "#/definitions/stat_information"
                },
                "Smithing": {
                    "$ref": "#/definitions/stat_information"
                },
                "Fishing": {
                    "$ref": "#/definitions/stat_information"
                },
                "Cooking": {
                    "$ref": "#/definitions/stat_information"
                },
                "Firemaking": {
                    "$ref": "#/definitions/stat_information"
                },
                "Woodcutting": {
                    "$ref": "#/definitions/stat_information"
                },
                "Farming": {
                    "$ref": "#/definitions/stat_information"
                },
                "Overall": {
                    "$ref": "#/definitions/stat_information"
                }
            },
            "required": [
                "Attack",
                "Strength",
                "Defence",
                "Ranged",
                "Prayer",
                "Magic",
                "Runecraft",
                "Construction",
                "Hitpoints",
                "Agility",
                "Herblore",
                "Thieving",
                "Crafting",
                "Fletching",
                "Slayer",
                "Hunter",
                "Mining",
                "Smithing",
                "Fishing",
                "Cooking",
                "Firemaking",
                "Woodcutting",
                "Farming",
                "Overall"
            ]
        },
        "status": {
            "title": "status",
            "description": "player status",
            "type": "object",
            "properties": {
                "hp": {
                    "title": "Hp",
                    "type": "integer"
                },
                "base_hp": {
                    "title": "Base Hp",
                    "type": "integer"
                },
                "prayer": {
                    "title": "Prayer",
                    "type": "integer"
                },
                "base_prayer": {
                    "title": "Base Prayer",
                    "type": "integer"
                },
                "run_energy": {
                    "title": "Run Energy",
                    "type": "integer"
                },
                "special_attack": {
                    "title": "Special Attack",
                    "type": "integer"
                }
            },
            "required": [
                "hp",
                "base_hp",
                "prayer",
                "base_prayer",
                "run_energy",
                "special_attack"
            ]
        },
        "location": {
            "title": "location",
            "description": "location model",
            "type": "object",
            "properties": {
                "x": {
                    "title": "X",
                    "type": "integer"
                },
                "y": {
                    "title": "Y",
                    "type": "integer"
                },
                "regionX": {
                    "title": "Regionx",
                    "type": "integer"
                },
                "regionY": {
                    "title": "Regiony",
                    "type": "integer"
                },
                "regionID": {
                    "title": "Regionid",
                    "type": "integer"
                },
                "plane": {
                    "title": "Plane",
                    "type": "integer"
                },
                "world": {
                    "title": "World",
                    "type": "integer"
                }
            },
            "required": [
                "x",
                "y",
                "regionX",
                "regionY",
                "regionID",
                "plane",
                "world"
            ]
        },
        "inventory_item": {
            "title": "inventory_item",
            "description": "inventory_item model",
            "type": "object",
            "properties": {
                "item_id": {
                    "title": "Item Id",
                    "type": "integer"
                },
                "item_amount": {
                    "title": "Item Amount",
                    "type": "integer"
                }
            },
            "required": [
                "item_id",
                "item_amount"
            ]
        },
        "prayer_slot": {
            "title": "prayer_slot",
            "description": "prayer slot",
            "type": "object",
            "properties": {
                "prayer_name": {
                    "title": "Prayer Name",
                    "type": "string"
                },
                "prayer_varbit": {
                    "title": "Prayer Varbit",
                    "type": "integer"
                }
            },
            "required": [
                "prayer_name",
                "prayer_varbit"
            ]
        },
        "equipment_item": {
            "title": "equipment_item",
            "type": "object",
            "properties": {
                "item_id": {
                    "title": "Item Id",
                    "type": "integer"
                },
                "item_amount": {
                    "title": "Item Amount",
                    "type": "integer"
                }
            },
            "required": [
                "item_id"
            ]
        },
        "equipment": {
            "title": "equipment",
            "type": "object",
            "properties": {
                "head": {
                    "$ref": "#/definitions/equipment_item"
                },
                "cape": {
                    "$ref": "#/definitions/equipment_item"
                },
                "amulet": {
                    "$ref": "#/definitions/equipment_item"
                },
                "ammo": {
                    "$ref": "#/definitions/equipment_item"
                },
                "weapon": {
                    "$ref": "#/definitions/equipment_item"
                },
                "body": {
                    "$ref": "#/definitions/equipment_item"
                },
                "shield": {
                    "$ref": "#/definitions/equipment_item"
                },
                "legs": {
                    "$ref": "#/definitions/equipment_item"
                },
                "gloves": {
                    "$ref": "#/definitions/equipment_item"
                },
                "boots": {
                    "$ref": "#/definitions/equipment_item"
                },
                "ring": {
                    "$ref": "#/definitions/equipment_item"
                }
            }
        },
        "player": {
            "title": "player",
            "description": "player model",
            "type": "object",
            "properties": {
                "discord": {
                    "title": "Discord",
                    "type": "string"
                },
                "stats": {
                    "$ref": "#/definitions/stats"
                },
                "status": {
                    "$ref": "#/definitions/status"
                },
                "location": {
                    "$ref": "#/definitions/location"
                },
                "inventory": {
                    "title": "Inventory",
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/inventory_item"
                    }
                },
                "prayer": {
                    "title": "Prayer",
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/prayer_slot"
                    }
                },
                "equipment": {
                    "$ref": "#/definitions/equipment"
                },
                "runewatch": {
                    "title": "Runewatch",
                    "type": "string"
                },
                "wdr": {
                    "title": "Wdr",
                    "type": "string"
                },
                "gamestate": {
                    "title": "Gamestate",
                    "type": "integer"
                },
                "verified": {
                    "title": "Verified",
                    "type": "boolean"
                },
                "rating": {
                    "title": "Rating",
                    "type": "integer"
                },
                "kick_list": {
                    "title": "Kick List",
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "promote_list": {
                    "title": "Promote List",
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "user_id": {
                    "title": "User Id",
                    "type": "integer"
                },
                "login": {
                    "title": "Login",
                    "type": "string"
                },
                "isPartyLeader": {
                    "title": "Ispartyleader",
                    "default": false,
                    "type": "boolean"
                }
            },
            "required": [
                "discord",
                "user_id",
                "login"
            ]
        }
    }
}
```

#### PingData
```
{
    "title": "ping",
    "description": "ping model",
    "type": "object",
    "properties": {
        "username": {
            "title": "Username",
            "type": "string"
        },
        "x": {
            "title": "X",
            "type": "integer"
        },
        "y": {
            "title": "Y",
            "type": "integer"
        },
        "regionX": {
            "title": "Regionx",
            "type": "integer"
        },
        "regionY": {
            "title": "Regiony",
            "type": "integer"
        },
        "regionID": {
            "title": "Regionid",
            "type": "integer"
        },
        "plane": {
            "title": "Plane",
            "type": "integer"
        },
        "color_r": {
            "title": "Color R",
            "type": "integer"
        },
        "color_g": {
            "title": "Color G",
            "type": "integer"
        },
        "color_b": {
            "title": "Color B",
            "type": "integer"
        },
        "color_alpha": {
            "title": "Color Alpha",
            "type": "integer"
        },
        "isAlert": {
            "title": "Isalert",
            "type": "boolean"
        }
    },
    "required": [
        "username",
        "x",
        "y",
        "regionX",
        "regionY",
        "regionID",
        "plane",
        "color_r",
        "color_g",
        "color_b",
        "color_alpha",
        "isAlert"
    ]
}
```
---

# Setting up your environment

__Requirements__
* Ubuntu 22.04 or a server with Ubuntu 22.04

### INSTALLING NGINX
```
sudo apt update
sudo apt install nginx
sudo ufw allow 'Nginx HTTP'
sudo ufw allow 22 #ssh
sudo ufw allow 80 # http
sudo ufw allow 443 # https
sudo ufw allow 3306 # Mysql
sudo ufw allow 5500 # NeverScapeAlone main branch
sudo ufw allow 5501 # NeverScapeAlone development branch
sudo ufw allow 6379 # Redis
sudo ufw enable
sudo ufw reload
sudo ufw status
```

### INSTALLING MYSQL
```
sudo apt install mysql-server
sudo mysql
```
```
> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
> FLUSH PRIVILEGES;
> exit
```

### INSTALLING PHP
```
sudo apt install php-fpm php-mysql
sudo nano /etc/nginx/sites-available/site
```

#### INPUT THE FOLLOWING
```
server {
        listen 80;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name site;

        location / {
                try_files $uri $uri/ =404;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
}
```

```
sudo ln -s /etc/nginx/sites-available/site /etc/nginx/sites-enabled/
sudo unlink /etc/nginx/sites-enabled/default
sudo systemctl reload nginx
```

### INSTALLING DOCKER
```
sudo apt-get update
sudo apt-get install \
                ca-certificates \
                curl \
                gnupg \
                lsb-release

sudo mkdir -p /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo service docker start
sudo docker run hello-world
```

### INSTALLING DOCKER-COMPOSE
```
sudo apt install docker-compose
```

### OPENING MYSQL TO THE WORLD
```
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```
#### CHANGE BIND ADDRESS TO THIS:
```
bind_address = {YOUR IPV4 HERE}
```
```
sudo service mysql restart
systemctl status mysql.service
sudo mysql -u root -p
```
#### ENTER YOUR PASSWORD "password" if you didn't change the default
```
> CREATE USER 'username'@'%' IDENTIFIED BY 'chooseyourpassword';
> GRANT ALL PRIVILEGES ON *.* TO 'username'@'%';
> FLUSH PRIVILEGES;
> exit
```
```
sudo systemctl restart nginx
```

### INSTALLING PHPMYADMIN
```
sudo apt install phpmyadmin
sudo nano /etc/nginx/snippets/phpmyadmin.conf
```
#### PLACE THIS IN THE phpmyadmin.conf FILE
```
location /phpmyadmin {
    root /usr/share/;
    index index.php index.html index.htm;
    location ~ ^/phpmyadmin/(.+\.php)$ {
        try_files $uri =404;
        root /usr/share/;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include /etc/nginx/fastcgi_params;
    }

    location ~* ^/phpmyadmin/(.+\.(jpg|jpeg|gif|css|png|js|ico|html|xml|txt))$ {
        root /usr/share/;
    }
}
```
```
sudo nano /etc/nginx/sites-available/site
```
#### REPLACE THE OLD FILE WITH THIS
```
server {
        listen 80;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name site;
        include snippets/phpmyadmin.conf;

        location / {
                try_files $uri $uri/ =404;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
}
```
```
sudo service nginx restart
```
#### you can now go to http://{youripv4domain}.com/phpmyadmin and login to your mysql database

### Entering in the NeverScapeAlone-API mysql files:
Use the file located here to generate a series of tables that you will use for your mysql database:
https://github.com/NeverScapeAlone/NeverScapeAlone-SQL/blob/main/full_setup.sql

### INSTALLING REDIS
```
sudo apt update
sudo apt install redis-server
sudo nano /etc/redis/redis.conf
```
#### IN THE redis.conf file, change the following lines:
```
> supervised no -> supervised systemd
> bind 127.0.0.1 ::-1 -> bind 0.0.0.0
> #requirepass -> requirepass <put a strong password here>
```
```
sudo systemctl restart redis.service
sudo systemctl status redis
redis-cli
```
```
> Auth <your very strong password from requirepass>
> ping
>> PONG
> exit
```

### GITHUB RUNNER
1. On your fork of the repository go to:
2. Settings > Actions > Runners > new self-hosted runner
3. Follow the commands listed
4. Set up your runner as a service here: https://docs.github.com/en/actions/hosting-your-own-runners/configuring-the-self-hosted-runner-application-as-a-service
```
sudo ./svc.sh install
sudo ./svc.sh start
```

### GITHUB REPOSITORY
1. Install VsCode
2. Install Github Desktop
3. Fork this repository.
4. Create a .env file in the root directory with the following parameters:

```
sql_uri = mysql+asyncmy://username:password@serveripv4:3306/databasename
discord_route_token = "a discord bot token goes here"
redis_password = "redis password goes here"
redis_database="1"
redis_port=6379
rate_limit_minute=120
rate_limit_hour=7200
match_version="v0.0.0-alpha"
```

5. go to the notes.md file and run the following. This will put you in a python venv, you will need to install python on your system prior.
```
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

6. Run `uvicorn api.app:app --reload` in the terminal. This will give you a local instance of the API to develop on. To deploy this, you can use the current workflow commands to execute it on your server.

7. Prior to running this on your site, make sure to correctly configure the your ports, and to set GITHUB SECRETS! Check the .github/workflows file for the github secrets you'll need, and the branches that will be activated. 

Feel free to leave a question in the issues page of this discord if you need help setting up your environment. 