using System;
using System.Text;

namespace Nx
{
    public class User
    {
        public string id;
        public string name;
        public string fullName;
        public string email;
        public string permissions;

        // Password-related data
        public string realm;
        public string hash;
        public string digest;

        private static string md5(string input)
        {
            // Use input string to calculate MD5 hash
            using (System.Security.Cryptography.MD5 md5 = System.Security.Cryptography.MD5.Create())
            {
                byte[] inputBytes = System.Text.Encoding.ASCII.GetBytes(input);
                byte[] hashBytes = md5.ComputeHash(inputBytes);

                // Convert the byte array to hexadecimal string
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < hashBytes.Length; i++)
                {
                    sb.Append(hashBytes[i].ToString("X2"));
                }
                return sb.ToString().ToLower();
            }
        }

        public void setPassword(string password)
        {
            Random rnd = new Random();
            string salt = rnd.Next(0, 16).ToString("X2");

            hash = "md5";
            hash += '$';
            hash += salt;
            hash += '$';
            hash += md5(salt + password);

            digest = md5($"{name.ToLower()}:{realm}:{password}");
        }
    }
}
