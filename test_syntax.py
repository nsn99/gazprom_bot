#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class TestClass:
    def __init__(self):
        self.value = None
        
    async def test_method(self):
        """Test method"""
        print("Test method called")
        return True

if __name__ == "__main__":
    test = TestClass()
    print("Syntax test passed")