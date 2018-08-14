using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Nx
{

    class RuntimeData
    {
        public class Peer
        {
            public string id;
            public string instanceId;
            public string peerType;
        }

        public Peer peer = new Peer();
        public string videoWallInstanceGuid;

    }

    class videowall_client
    {
        static string host = "localhost";
        static int port = 7001;
        static string videoWallId = "{c9a802fc-aa33-4afb-8701-a3943e8153ba}";
        static string screenId = "{3b25cc0a-8a7c-458c-adc8-8e173a9b8d7f}";
        static string moduleId = "{98b5dfa1-1882-434b-ad56-9b2f4ec69905}";
        static string runtimeId = "{368ee6da-7608-45a4-9867-5a0af04c7e8d}";

        private HttpClient client;
        private Thread transactionsThread;
        private JsonSerializer serializer = new JsonSerializer();
        private bool m_stopping = false;

        public Queue<string> lines = new Queue<string>();

        // Makes proper uri
        protected Uri MakeUri(string path, string query)
        {
            return new UriBuilder()
            {
                Port = port,
                Scheme = Uri.UriSchemeHttp,
                Host = host,
                Path = path,
                Query = query,
            }.Uri;
        }

        public void initConnection()
        {
            var credCache = new CredentialCache();
            var sampleUri = MakeUri("", "");
            credCache.Add(sampleUri, "Digest", new NetworkCredential(videoWallId, ""));

            client = new HttpClient( new HttpClientHandler { Credentials = credCache});
            client.DefaultRequestHeaders.Add("X-Version","1");
            client.DefaultRequestHeaders.Add("X-NetworkOptix-VideoWall", videoWallId);
            client.DefaultRequestHeaders.Add("X-runtime-guid", runtimeId);
        }

        public void startReceivingNotificaitions()
        {
            transactionsThread = new Thread(() =>
            {
                var eventsUri = MakeUri("ec2/events",
                    "format=json&peerType=PT_VideowallClient&runtime-guid=" + runtimeId);
                var stream = client.GetStreamAsync(eventsUri).GetAwaiter().GetResult();
                var reader = new StreamReader(stream);
                while (!m_stopping)
                {
                    var line = reader.ReadLine();
                    lock(lines)
                    {
                        lines.Enqueue(line);
                    }
                }
            });
            transactionsThread.Start();
        }

        public void sendRequest(string path, string data)
        {
            var uri = MakeUri(path, "");
            var reqContent = new StringContent(data);
            reqContent.Headers.ContentType = new MediaTypeHeaderValue("application/json");
            try
            {
                var response = client.PostAsync(uri, reqContent).GetAwaiter().GetResult();
                if (response.StatusCode != System.Net.HttpStatusCode.OK)
                {
                    Console.WriteLine(path + ": got http error response: " + response.ToString());
                    Console.WriteLine("response contents: " + response.Content.ToString());
                }
                else
                {
                    Console.WriteLine(path + ": got http success response: " + response.ToString());
                }
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine("Got an http error during request: " + ex.ToString());
            }
        }

        public void sendRuntimeData()
        {
            var runtimeData = new RuntimeData();
            runtimeData.peer.id = moduleId;
            runtimeData.peer.instanceId = runtimeId;
            runtimeData.peer.peerType = "PT_VideowallClient";
            runtimeData.videoWallInstanceGuid = screenId;

            var writer = new StringWriter();
            using (var jsonWriter = new JsonTextWriter(writer))
                serializer.Serialize(jsonWriter, runtimeData);
            sendRequest("ec2/runtimeInfoChanged", writer.ToString());
        }


        public void stopReceivingNotificaitions()
        {
            m_stopping = true;
            transactionsThread.Join();
        }

        static void Main(string[] args)
        {
            var client = new videowall_client();
            client.initConnection();
            client.startReceivingNotificaitions();
            client.sendRuntimeData();

            string command;
            do
            {
                command = Console.ReadLine();
                if (command == "p")
                {
                    lock(client.lines)
                    {
                        foreach (var line in client.lines)
                            Console.WriteLine(line);
                        client.lines.Clear();
                    }
                }
            } while (command != "q");
            client.stopReceivingNotificaitions();
            Console.WriteLine("Please wait while connection is closing...");
        }
    }
}
