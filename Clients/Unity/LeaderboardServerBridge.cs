using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public class LeaderboardServerBridge : MonoBehaviour
{
    public string serverEndpoint = "https://exploitavoid.com/api";
    public int leaderboardID = 15;
    public string leaderboardSecret = "3f2981858c7ff90dd6eaffc4a93589cc";
    
    public async Task<List<LeaderboardEntry>> RequestEntries(int start, int count)
    {
        string url = serverEndpoint + $"/getscoreentries?id={leaderboardID}&start={start}&count={count}";
        using (UnityWebRequest unityWebRequest = UnityWebRequest.Get(url))
        {
            await unityWebRequest.SendWebRequestAsync();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    break;
                case UnityWebRequest.Result.Success:
                    List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(unityWebRequest.downloadHandler.text);
                    return scores;
            }
        }
        return null;
    }

    public async Task<LeaderboardEntry> RequestUserEntry(string name)
    {
        string url = serverEndpoint + $"/getscoreentries?id={leaderboardID}&start=1&count=1&search={name}";
        using (UnityWebRequest unityWebRequest = UnityWebRequest.Get(url))
        {
            await unityWebRequest.SendWebRequestAsync();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    break;
                case UnityWebRequest.Result.Success:
                    List <LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(unityWebRequest.downloadHandler.text);
                    if(scores != null && scores.Count > 0)
                    {
                        return scores[0];
                    }
                    return null;
            }
        }
        return null;
    }

    public async Task<bool> SendUserValue(string name, float value)
    {
        string url = serverEndpoint + "/submitscoreentry";

        string uploadJson = $"{{\"name\":\"{name}\", \"value\":{value}, \"id\":{leaderboardID}}}";
        string toHash = "/submitscoreentry" + uploadJson + leaderboardSecret;

        byte[] utfBytes = Encoding.UTF8.GetBytes(toHash);
        byte[] result;
        SHA256 shaM = new SHA256Managed();
        result = shaM.ComputeHash(utfBytes);

        string hashString = BitConverter.ToString(result).Replace("-", "");

        byte[] rawBytes = Encoding.ASCII.GetBytes(uploadJson + hashString);

        DownloadHandlerBuffer d = new DownloadHandlerBuffer();
        UploadHandlerRaw u = new UploadHandlerRaw(rawBytes);
        using (UnityWebRequest unityWebRequest = new UnityWebRequest(url, "POST", d, u))
        {
            await unityWebRequest.SendWebRequestAsync();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    break;
                case UnityWebRequest.Result.Success:
                    return true;
            }
        }
        return false;
    }

    T DeserializeJson<T>(string result)
    {
        DataContractJsonSerializer jsonSer = new DataContractJsonSerializer(typeof(T));
        using MemoryStream ms = new MemoryStream(Encoding.UTF8.GetBytes(result))
        {
            Position = 0
        };
        return (T)jsonSer.ReadObject(ms);
    }
}

public static class WebRequestAsyncExtension
{
    public static Task<AsyncOperation> SendWebRequestAsync(this UnityWebRequest unityWebRequest)
    {
        TaskCompletionSource<AsyncOperation> taskCompletionSource = new TaskCompletionSource<AsyncOperation>();
        unityWebRequest.SendWebRequest().completed += x => taskCompletionSource.SetResult(x);
        return taskCompletionSource.Task;
    }
}

[DataContract]
public class LeaderboardEntry
{
    [DataMember]
    public string name;
    [DataMember(Name = "value")]
    public float value;
    [DataMember]
    public int position;
}