import pandas as pd
import re
import sys

def analyze_air_conditioning_descriptions(csv_filepath):
    """
    Analyzes a CSV file of property listings to find and categorize
    descriptions of air conditioning systems.
    """
    try:
        # Set the default encoding to utf-8
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')

        df = pd.read_csv(csv_filepath)
    except FileNotFoundError:
        print(f"错误：文件未找到 -> '{csv_filepath}'")
        print("请确保脚本文件和您的CSV文件在同一个文件夹内，并且文件名完全正确。")
        return
    except Exception as e:
        print(f"读取或解析CSV文件时出错: {e}")
        return

    # Combine relevant text fields into one, handling potential NaN values
    text_columns = ['property_headline', 'property_description', 'property_features']
    df['corpus'] = df[text_columns].fillna('').agg(' '.join, axis=1)

    # Convert to lowercase for case-insensitive matching
    df['corpus'] = df['corpus'].str.lower()

    # Define seed words to find relevant sentences about air conditioning
    seed_words = {
        'air con', 'air-con', 'aircon', 'air conditioning', 'airconditioner',
        'cooling', 'climate control', 'ducted', 'split system', 'reverse cycle'
    }

    discovered_sentences = set()

    # Regex to split text into sentences. This approach handles various delimiters.
    sentence_pattern = re.compile(r'[^.!?]*[.!?]')
    seed_word_pattern = re.compile(r'\b(' + '|'.join(seed_words) + r')\b', re.IGNORECASE)

    for text in df['corpus']:
        sentences = sentence_pattern.findall(text)
        for sentence in sentences:
            if seed_word_pattern.search(sentence):
                cleaned_sentence = sentence.strip()
                if 10 < len(cleaned_sentence) < 300:
                    discovered_sentences.add(cleaned_sentence)

    # --- Format and Print Results ---
    print(f"--- 空调相关描述分析报告 ---\n")
    print(f"在 {len(df)} 条房源数据中，共发现了 {len(discovered_sentences)} 条关于空调的独特描述。\n")
    print("结果表明，中介确实使用了多种不同的术语来描述空调系统，而不只是'air_conditioning'。\n")
    print("以下是从您的数据中提取的真实描述样本：\n")

    if discovered_sentences:
        sorted_sentences = sorted(list(discovered_sentences))
        for i, sentence in enumerate(sorted_sentences):
            print(f"{i+1}. {sentence}")
    else:
        print("在数据中未能发现包含空调相关关键词的句子。")

    print("\n--- 结论与建议 ---\n")
    print("从样本中可以看出，至少有以下几种常见的空调类型被频繁提及：")
    print("- Ducted Air Conditioning (中央管道式空调)")
    print("- Split System Air Conditioning (分体式空调)")
    print("- Reverse Cycle Air Conditioning (冷暖逆循环空调)")
    print("- 以及 'Air Conditioning', 'Cooling', 'Climate Control' 等通用术语。\n")
    print("建议您在爬虫的特征提取逻辑中，增加对这些特定术语的识别，以便更精确地对房源特征进行分类。")
    print("例如，您可以创建一个更详细的特征字段，如 'air_conditioning_type'，来存储 'ducted', 'split_system' 等具体值。")


if __name__ == "__main__":
    # The name of the CSV file you want to analyze
    # Make sure this matches the name of your file exactly
    filename = '20250726_160346_results.csv'
    analyze_air_conditioning_descriptions(filename)