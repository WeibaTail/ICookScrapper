#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
愛料理網站爬蟲程式 - 簡潔高效版
功能：爬取愛料理網站的食譜資訊，包括食譜名稱、URL和食材清單
輸出：符合指定格式的CSV檔案，Excel可正確顯示中文
作者：AI助手
建立日期：2025-06-05
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import time
import random
from urllib.parse import urljoin

class ICookScraper:
    """愛料理網站爬蟲類別"""
    
    def __init__(self):
        """初始化爬蟲設定"""
        self.base_url = "https://icook.tw"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
    
    def search_recipes(self, keyword, page_limit=2):
        """搜索食譜並返回URL列表
        
        參數:
            keyword (str): 搜索關鍵字
            page_limit (int): 搜索頁數限制
            
        返回:
            list: 食譜URL列表
        """
        recipe_urls = []
        search_url = f"{self.base_url}/search/{keyword}" if keyword else f"{self.base_url}/recipes"
        
        for page in range(1, page_limit + 1):
            try:
                url = f"{search_url}?page={page}" if page > 1 else search_url
                print(f"正在搜索頁面: {url}")
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=re.compile(r'/recipes/\d+'))
                
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        recipe_urls.append(full_url)
                
                print(f"在第{page}頁找到 {len(links)} 個食譜連結")
                time.sleep(random.uniform(1, 2))  # 延遲避免被封鎖
                
            except Exception as e:
                print(f"搜索第{page}頁時出錯: {e}")
                continue
        
        return list(set(recipe_urls))  # 去除重複URL
    
    def get_recipe_info(self, recipe_url):
        """爬取單一食譜資訊
        
        參數:
            recipe_url (str): 食譜頁面URL
            
        返回:
            dict: 包含食譜名稱、URL和食材資訊的字典
        """
        try:
            print(f"正在爬取: {recipe_url}")
            response = self.session.get(recipe_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取食譜名稱
            recipe_name = ""
            title_element = soup.find('h1')
            if title_element:
                recipe_name = title_element.get_text().strip()
                if "by" in recipe_name:
                    recipe_name = recipe_name.split("by")[0].strip()
            
            # 尋找食材資訊
            ingredients = []
            
            # 方法1: 尋找食材列表
            ingredients_sections = soup.find_all(['h2', 'h3', 'div'], string=re.compile(r'食材|材料'))
            for section in ingredients_sections:
                # 找到ul元素 (可能在父節點或兄弟節點中)
                parent = section.parent
                ul_element = parent.find('ul') if parent else None
                
                if not ul_element:
                    for sibling in section.next_siblings:
                        if hasattr(sibling, 'name') and sibling.name == 'ul':
                            ul_element = sibling
                            break
                
                if ul_element:
                    for li in ul_element.find_all('li'):
                        text = li.get_text().strip()
                        # 過濾非食材項目
                        if len(text) < 50 and not text.startswith(('#', '●')):
                            # 提取食材名稱和用量
                            a_tag = li.find('a')
                            if a_tag:
                                name = a_tag.get_text().strip()
                                amount = text.replace(name, '').strip()
                            else:
                                # 用正則表達式分離名稱和用量
                                match = re.match(r'^([^0-9]+)([0-9].*)$', text)
                                if match:
                                    name = match.group(1).strip()
                                    amount = match.group(2).strip()
                                else:
                                    name = text
                                    amount = ''
                            
                            if name:
                                ingredients.append({"name": name, "amount": amount})
                    
                    if ingredients:  # 找到食材就跳出循環
                        break
            
            # 方法2: 如果上面沒找到，查找data-targeting屬性
            if not ingredients:
                for div in soup.find_all('div', attrs={"data-targeting": True}):
                    targeting = div.get('data-targeting', '')
                    if 'ingredients' in targeting:
                        try:
                            import json
                            data = json.loads(targeting.replace('&quot;', '"'))
                            if 'ingredients' in data:
                                for ingredient in data['ingredients']:
                                    ingredients.append({"name": ingredient, "amount": ""})
                        except:
                            pass
            
            # 去除重複食材
            seen = set()
            unique_ingredients = []
            for item in ingredients:
                if item['name'] not in seen:
                    seen.add(item['name'])
                    unique_ingredients.append(item)
            
            # 格式化輸出
            ingredients_text = ", ".join([f"{item['name']}{item['amount']}" for item in unique_ingredients])
            formatted_output = f"{recipe_name},{recipe_url},{ingredients_text}"
            
            return {
                "recipe_name": recipe_name,
                "url": recipe_url,
                "ingredients": unique_ingredients,
                "formatted_output": formatted_output
            }
            
        except Exception as e:
            print(f"爬取食譜時出錯: {e}")
            return None
    
    def save_to_csv(self, data, filename):
        """將食譜資料儲存為CSV格式
        
        參數:
            data (list): 食譜資料列表
            filename (str): 輸出檔案名稱
        """
        if not data:
            print("沒有資料可儲存")
            return
        
        try:
            # 使用utf-8-sig編碼，確保Excel可正確顯示中文
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                for item in data:
                    if item and item["formatted_output"]:
                        csvfile.write(item["formatted_output"] + "\n")
            
            print(f"資料已儲存至 {filename}")
            print(f"總共儲存了 {len(data)} 筆食譜資料")
            
        except Exception as e:
            print(f"儲存CSV檔案時出錯: {e}")
    
    def run(self, keywords, max_recipes=20, output_file='icook_recipes.csv'):
        """執行爬蟲主程式
        
        參數:
            keywords (list): 搜索關鍵字列表
            max_recipes (int): 最大爬取食譜數量
            output_file (str): 輸出檔案名稱
            
        返回:
            list: 爬取的食譜資料列表
        """
        all_urls = []
        
        # 搜索食譜URL
        for keyword in keywords:
            print(f"\n搜索關鍵字: {keyword}")
            urls = self.search_recipes(keyword, page_limit=1)
            all_urls.extend(urls)
            time.sleep(random.uniform(1, 2))
        
        # 去重並限制數量
        unique_urls = list(set(all_urls))[:max_recipes]
        print(f"\n將爬取 {len(unique_urls)} 個食譜")
        
        # 爬取食譜資訊
        results = []
        for i, url in enumerate(unique_urls, 1):
            print(f"\n進度: {i}/{len(unique_urls)}")
            recipe_info = self.get_recipe_info(url)
            if recipe_info and recipe_info["formatted_output"]:
                results.append(recipe_info)
            time.sleep(random.uniform(1, 3))
        
        # 儲存結果
        self.save_to_csv(results, output_file)
        print(f"\n爬蟲完成！成功爬取 {len(results)} 個食譜")
        return results


def main():
    """主程式入口"""
    print("="*60)
    print("愛料理網站爬蟲程式 - 啟動中")
    print("功能：爬取愛料理網站的食譜資訊，包括食譜名稱、URL和食材清單")
    print("輸出格式：蘋果蜜汁豬柳(料理名),https://icook.tw/recipes/470233,蜂蜜1大匙, 蠔油1/2大匙,米酒1/2大匙")
    print("="*60)
    
    # 創建爬蟲實例
    scraper = ICookScraper()
    
    # 設定爬蟲參數
    keywords = ["雞肉", "豬肉", "湯品"]  # 可自行修改搜索關鍵字
    max_recipes = 40  # 可自行修改爬取數量
    output_file = "愛料理食譜資料.csv"  # 可自行修改輸出檔案名稱
    
    # 執行爬蟲
    scraper.run(keywords, max_recipes, output_file)


if __name__ == "__main__":
    main()