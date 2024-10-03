import sys
import pre_commit as pc

def main():
    success, msg = pc.check_output()
    if not success:
        print(f"***Error***\n{msg}")
        sys.exit(1)
    else:
        sys.exit(0)
        
if __name__ == "__main__":
    main()