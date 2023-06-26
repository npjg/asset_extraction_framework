

# Defines a general-purpose bounding box.
class BoundingBox:
    def __init__(self, top = None, left = None, bottom = None, right = None):
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right

        if self.top is not None and self.bottom is not None:
            assert self.bottom >= self.top
        
        if self.left and self.right:
            assert self.right >= self.left

    @property
    def width(self):
        if (self.left is not None) and (self.right is not None):
            return self.right - self.left

    @property
    def height(self):
        if (self.top is not None) and (self.bottom is not None):
            return self.bottom - self.top

    def __eq__(self, comparison):
        return (self.top == comparison.top) and \
            (self.left == comparison.left) and \
            (self.bottom == comparison.bottom) and \
            (self.right == comparison.right)
