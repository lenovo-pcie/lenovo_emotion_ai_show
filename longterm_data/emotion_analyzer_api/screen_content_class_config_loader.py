import os

def load_screen_content_class_config(config_path=None):
    """
    读取屏幕内容分类配置文件，返回分类字典列表和模型提示词字符串。
    :param config_path: 配置文件路径，默认与本文件同目录下 screen_content_class_config.txt
    :return: (class_list, prompt_str)
        class_list: [ {'id': 1, 'name': '即时通讯', 'desc': '...'}, ... ]
        prompt_str: 适合直接拼接到模型提示词的多行字符串
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'screen_content_class_config.txt')
    class_list = []
    prompt_lines = []
    with open(config_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 格式: <id>: <name>: <desc>
            parts = line.split(':', 2)
            if len(parts) == 3:
                class_id = parts[0].strip()
                class_name = parts[1].strip()
                class_desc = parts[2].strip()
                class_list.append({'id': int(class_id), 'name': class_name, 'desc': class_desc})
                prompt_lines.append(f"{class_id}. {class_name}: {class_desc}")
    # 加入分类建议
    prompt_lines.append('\n分类建议：')
    with open(config_path, encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('# 分类建议'):
                prompt_lines.append(line.strip('# ').strip())
            elif line.strip().startswith('# -'):
                prompt_lines.append(line.strip('# ').strip())
    prompt_str = '\n'.join(prompt_lines)
    return class_list, prompt_str

# 示例用法
if __name__ == '__main__':
    class_list, prompt = load_screen_content_class_config()
    print('分类列表:')
    for c in class_list:
        print(f"{c['id']}: {c['name']} - {c['desc']}")
    print('\n模型提示词:')
    print(prompt) 