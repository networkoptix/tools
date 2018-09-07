using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace Nx
{
    class videowall_client
    {
        static string host = "localhost";
        static int port = 7001;
        static string videoWallId = "{c9a802fc-aa33-4afb-8701-a3943e8153ba}";
        static string screenId = "{3b25cc0a-8a7c-458c-adc8-8e173a9b8d7f}";
        static string runtimeId = "{368ee6da-7608-45a4-9867-5a0af04c7e8d}";

        private HttpClient m_client;
        private Thread m_transactionsThread;
        private bool m_stopping = false;

        private Queue<string> lines = new Queue<string>();

        // Makes proper uri
        private Uri MakeUri(string path, string query)
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

        private class ControlMessage
        {
            public int operation;
            public string videowallGuid;
            public string instanceGuid;

            [JsonProperty(PropertyName="params")]
            public Dictionary<string, string> parameters;
        }

        private void initConnection()
        {
            var credCache = new CredentialCache();
            var sampleUri = MakeUri("", "");
            credCache.Add(sampleUri, "Digest", new NetworkCredential(videoWallId, ""));

            m_client = new HttpClient( new HttpClientHandler { Credentials = credCache});
            m_client.DefaultRequestHeaders.Add("X-Version","1");
            m_client.DefaultRequestHeaders.Add("X-NetworkOptix-VideoWall", videoWallId);
            m_client.DefaultRequestHeaders.Add("X-runtime-guid", runtimeId);
        }

        private JToken readTransaction(StreamReader reader)
        {
            // Skip lines until the multipart header.
            var line = reader.ReadLine();
            if (line != "--ec2boundary")
                return null;

            var contentType = reader.ReadLine();
            if (contentType != "Content-Type: application/json")
                return null;

            var contentLength = reader.ReadLine();
            Regex regex = new Regex(@"Content-Length: (\d+)");
            Match match = regex.Match(contentLength ?? "");
            if (!match.Success)
                return null;

            var length = int.Parse(match.Groups[1].Value);
            if (length == 0)
                return null;

            // Skip empty line before data.
            reader.ReadLine();

            var content = reader.ReadLine();
            return JObject.Parse(content)["tran"];
        }

        private void startReceivingNotifications()
        {
            m_transactionsThread = new Thread(() =>
            {
                var eventsUri = MakeUri("ec2/events",
                    "format=json" +
                    "&peerType=PT_VideowallClient" +    //< Must be here
                    $"&runtime-guid={runtimeId}" +
                    $"&videoWallInstanceGuid={screenId}");
                var stream = m_client.GetStreamAsync(eventsUri).GetAwaiter().GetResult();
                var reader = new StreamReader(stream);
                while (!m_stopping)
                {
                    var transaction = readTransaction(reader);
                    if (transaction == null)
                        continue;

                    int command = (int) transaction["command"];
                    lock(lines)
                    {
                        lines.Enqueue($"Got command {command}");
                    }

                    if (command == 703)
                    {
                        var controlMessage = transaction["params"].ToObject<ControlMessage>();
                        lock(lines)
                        {
                            string parameters = string.Join("\n",
                                controlMessage.parameters.Select((key, value) => $"{key}: {value}"));

                            lines.Enqueue($"Parsed control message operation {controlMessage.operation}" +
                                          $"sent to {controlMessage.videowallGuid}, {controlMessage.instanceGuid}" +
                                          $"with params {parameters}");
                        }
                    }
                }
            });
            m_transactionsThread.Start();
        }

        private void stopReceivingNotificaitions()
        {
            m_stopping = true;
            m_transactionsThread.Join();
        }

        static void Main(string[] args)
        {
            var client = new videowall_client();
            client.initConnection();
            client.startReceivingNotifications();

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
