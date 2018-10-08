using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace Nx
{
    public class Api
    {
        public Api(Connection connection)
        {
            m_connection = connection;
        }

        // Get a specific layout
        // @param id: layout Logical ID
        public async Task<Layout> getLayout(int id)
        {
            // We are expecting to get an array with a single element
            var layouts = await m_connection.get<Layout[]>("/ec2/getLayouts", $"id={id}");
            if (layouts == null || layouts.Length == 0)
                return null;
            return layouts[0];
        }

        public async Task<Layout> addCameraToLayout(Layout layout, int cameraId, int tileId)
        {
            int tileX = 0;
            int tileY = 0;
            layout.getTileCoords(tileId, out tileX, out tileY);

            bool contains = false;
            foreach (var item in layout.items)
            {
                // There is already an item in specified location (tileX, tileY)
                if (item.left == tileX && item.top == tileY)
                {
                    Debug.WriteLine("AddCameraToLayout: overriding tile info");
                    item.resourceId = ""; //< Existing id must be cleaned.
                    item.resourcePath = cameraId.ToString();
                    item.id = System.Guid.NewGuid().ToString();
                    contains = true;
                    break;
                }
            }

            // Adding new item if it is not already there.
            if (!contains)
            {
                Debug.WriteLine("AddCameraToLayout: adding new item to the layout");
                var item = new Layout.Item()
                {
                    left = tileX,
                    top = tileY,
                    right = tileX + 1,
                    bottom = tileY + 1,
                    flags = 1,
                    resourcePath = cameraId.ToString(),
                    id = System.Guid.NewGuid().ToString()
                };
                layout.items.Add(item);
            }

            // Sync this layout with the server
            await saveLayout(layout);

            return layout;
        }

        public async Task saveLayout(Layout layout)
        {
            await m_connection.post(layout, "/ec2/saveLayout");
        }

        public async Task<User[]> getUsers()
        {
            return await m_connection.get<User[]>("/ec2/getUsers");
        }

        public async Task saveUser(User user)
        {
            await m_connection.post(user, "/ec2/saveUser");
        }

        public async Task deleteUser(User user)
        {
            await m_connection.post(user, "/ec2/removeUser");
        }

        private Connection m_connection;
    }
}