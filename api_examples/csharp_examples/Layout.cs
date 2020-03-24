using System;
using System.Collections.Generic;

namespace Nx
{
    public class Layout
    {
        // Layout item
        public class Item
        {
            public string id;
            public int flags;
            public int left;
            public int right;
            public int top;
            public int bottom;
            public string resourceId;
            public string resourcePath;
        }

        public string id;
        public List<Item> items;

        public int fixedWidth;
        public int fixedHeight;

        public void getTileCoords(int tileId, out int x, out int y)
        {
            int w = Math.Max(fixedWidth, 1);
            int h = fixedHeight;
            int left = -(w / 2);
            int top = -(h / 2);
            x = tileId % w + left;
            y = tileId / w + top;
        }
    }
}
