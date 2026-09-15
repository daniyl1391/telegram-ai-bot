import sys
import importlib.util

def test_imports():
    """Test all imports work correctly"""
    print("Testing imports...")
    
    try:
        import bot.config
        print("✓ bot.config")
        
        import bot.database
        print("✓ bot.database")
        
        import bot.services.ai_manager
        print("✓ ai_manager")
        
        import bot.services.subscription
        print("✓ subscription")
        
        import bot.services.payment
        print("✓ payment")
        
        import bot.admin.panel
        print("✓ admin panel")
        
        from bot.handlers.start import start
        print("✓ start handler")
        
        from bot.handlers.admin import admin_menu
        print("✓ admin handler")
        
        print("\nAll imports successful!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        from bot.database import db
        
        # Test user operations
        db.add_user(12345, "testuser", "Test")
        user = db.get_user(12345)
        assert user is not None
        print("✓ User management works")
        
        # Test subscription
        db.create_subscription(12345, "free", 10, 30)
        sub = db.get_subscription(12345)
        assert sub is not None
        print("✓ Subscription works")
        
        # Test settings
        db.set_setting("test", "value")
        val = db.get_setting("test")
        assert val == "value"
        print("✓ Settings work")
        
        print("Database tests passed!")
        return True
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_imports() and test_database()
    sys.exit(0 if success else 1)
