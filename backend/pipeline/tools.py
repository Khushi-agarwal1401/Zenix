from typing import Any, Dict, List, Callable
import os
import sqlite3
import random
from .modules import RAGModule

class ToolRegistry:
    """
    Registry of tools available to the Agent.
    """
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.tools = {}
        self._register_tools()
        
    def _register_tools(self):
        # Register Search Tool
        self.tools["search"] = {
            "name": "search",
            "description": "Search the knowledge base for information.",
            "usage": "search: <query>",
            "handler": self._handle_search
        }
        
        # Register Database Tool
        self.tools["sql"] = {
            "name": "sql",
            "description": "Execute SQL queries on the database. Tables: users, orders.",
            "usage": "sql: SELECT * FROM users",
            "handler": self._handle_sql
        }
        
        # Register API Tool
        self.tools["api"] = {
            "name": "api",
            "description": "Fetch data from external APIs (Weather, Finance).",
            "usage": "api: get_weather <city> | api: get_stock <ticker>",
            "handler": self._handle_api
        }
        
        # Register File Tool
        self.tools["file"] = {
            "name": "file",
            "description": "Read file contents (Safe mode).",
            "usage": "file: read <filename>",
            "handler": self._handle_file
        }
        
        # Initialize Mock Database
        self._init_mock_db()

    def _init_mock_db(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, city TEXT)")
        cur.execute("INSERT INTO users (name, city) VALUES ('Alice', 'Mumbai'), ('Bob', 'Delhi'), ('Charlie', 'Bangalore')")
        cur.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, item TEXT, amount REAL)")
        cur.execute("INSERT INTO orders (user_id, item, amount) VALUES (1, 'Laptop', 1200.00), (2, 'Phone', 800.00)")
        self.conn.commit()
        
    def _handle_search(self, query: str) -> str:
        if not self.rag_engine:
            return "Error: Search engine not available."
            
        results = self.rag_engine.search(query, k=2)
        if not results:
             return "No results found."
             
        return "\n".join([f"- {r['content']}" for r in results])

    def _handle_sql(self, query: str) -> str:
        try:
            cur = self.conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            if not rows:
                return "Query returned no results."
            return str(rows)
        except Exception as e:
            return f"SQL Error: {e}"

    def _handle_api(self, args: str) -> str:
        args = args.lower().strip()
        if "weather" in args:
            city = args.replace("get_weather", "").strip()
            # Mock weather
            conditions = ["Sunny", "Cloudy", "Rainy", "Haze"]
            temp = random.randint(20, 35)
            return f"Weather in {city}: {random.choice(conditions)}, {temp}°C"
        elif "stock" in args:
            ticker = args.replace("get_stock", "").strip().upper()
            price = random.randint(100, 2000)
            return f"Stock {ticker}: ${price}.00 (Mock Data)"
        return "Unknown API endpoint."

    def _handle_file(self, args: str) -> str:
        # Mock File System for safety
        mock_files = {
            "report.txt": "This is the Q1 sales report. Revenue is up 20%.",
            "data.csv": "id,name,value\n1,A,10\n2,B,20"
        }
        filename = args.replace("read", "").strip()
        
        if filename in mock_files:
            return f"Content of {filename}:\n{mock_files[filename]}"
            
        return "File not found or access denied."

    def get_tool_descriptions(self) -> str:
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"{name}: {tool['description']} Usage: {tool['usage']}")
        return "\n".join(descriptions)
        
    def execute(self, tool_name: str, args: str) -> str:
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found."
            
        try:
            return tool["handler"](args)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"
