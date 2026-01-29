from clients.python.plastic_memories_client import PlasticMemoriesClient, Message


def main():
    client = PlasticMemoriesClient(
        base_url="http://127.0.0.1:8007",
        user_id="local",
        persona_id="default",
        source_app="python_sdk_demo",
    )

    client.persona_create(meta={"display_name": "Ava", "description": "默认人格"})
    client.append_messages([
        Message(role="user", content="请默认中文回答"),
        Message(role="user", content="回答工程化"),
    ])
    client.write([
        Message(role="user", content="叫我 tcmiku"),
    ])

    result = client.recall("我喜欢什么风格的回答？")
    print("==== injection_block ====")
    print(result.injection_block)


if __name__ == "__main__":
    main()
