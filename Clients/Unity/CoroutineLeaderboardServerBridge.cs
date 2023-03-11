using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Globalization;
using System.Web;
using UnityEngine;
using UnityEngine.Networking;

public class CoroutineLeaderboardServerBridge : MonoBehaviour
{
    public string serverEndpoint = "https://exploitavoid.com/leaderboards/v1/api";
    public int leaderboardID = 3;
    public string leaderboardSecret = "656433a96b56132affbfde59758acc44";

    public Coroutine RequestEntries(int start, int count, Action<List<LeaderboardEntry>> successCallback, Action errorCallback)
    {
        return StartCoroutine(RequestEntriesCoroutine(start, count, successCallback, errorCallback));
    }

    IEnumerator RequestEntriesCoroutine(int start, int count, Action<List<LeaderboardEntry>> successCallback, Action errorCallback)
    {
        string url = serverEndpoint + $"/get_entries?leaderboard_id={leaderboardID}&start={start}&count={count}";
        using (UnityWebRequest unityWebRequest = UnityWebRequest.Get(url))
        {
            yield return unityWebRequest.SendWebRequest();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    Debug.LogError(unityWebRequest.downloadHandler.text);
                    errorCallback.Invoke();
                    break;
                case UnityWebRequest.Result.Success:
                    List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(unityWebRequest.downloadHandler.text);
                    successCallback.Invoke(scores);
                    break;
            }
        }
    }

    public Coroutine RequestUserEntry(string name, Action<LeaderboardEntry> successCallback, Action errorCallback)
    {
        return StartCoroutine(RequestUserEntryCoroutine(name, successCallback, errorCallback));
    }

    IEnumerator RequestUserEntryCoroutine(string name, Action<LeaderboardEntry> successCallback, Action errorCallback)
    {
        string urlEncodedName = HttpUtility.UrlEncode(name);
        string url = serverEndpoint + $"/get_entries?leaderboard_id={leaderboardID}&start=1&count=1&search={urlEncodedName}";
        using (UnityWebRequest unityWebRequest = UnityWebRequest.Get(url))
        {
            yield return unityWebRequest.SendWebRequest();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    Debug.LogError(unityWebRequest.downloadHandler.text);
                    errorCallback.Invoke();
                    break;
                case UnityWebRequest.Result.Success:
                    List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(unityWebRequest.downloadHandler.text);
                    if (scores != null && scores.Count > 0)
                    {
                        successCallback.Invoke(scores[0]);
                    }
                    else
                    {
                        errorCallback.Invoke();
                    }
                    break;
            }
        }
    }

    public Coroutine SendUserValue(string name, int value, Action successCallback, Action errorCallback)
    {
        return StartCoroutine(SendUserValueCoroutine(name, value, successCallback, errorCallback));
    }

    public Coroutine SendUserValue(string name, float value, Action successCallback, Action errorCallback)
    {
        return StartCoroutine(SendUserValueCoroutine(name, value, successCallback, errorCallback));
    }

    public Coroutine SendUserValue(string name, double value, Action successCallback, Action errorCallback)
    {
        return StartCoroutine(SendUserValueCoroutine(name, value, successCallback, errorCallback));
    }

    IEnumerator SendUserValueCoroutine(string name, IConvertible value, Action successCallback, Action errorCallback)
    {
        string url = serverEndpoint + "/update_entry";
        string valueString = value.ToString(CultureInfo.InvariantCulture);
        string uploadJson = SerializeJson(new EntryUpdate(name, valueString, leaderboardID));
        string toHash = "/update_entry" + uploadJson + leaderboardSecret;

        byte[] utfBytes = Encoding.UTF8.GetBytes(toHash);
        byte[] result;
        SHA256 shaM = new SHA256Managed();
        result = shaM.ComputeHash(utfBytes);

        string hashString = BitConverter.ToString(result).Replace("-", "");

        byte[] rawBytes = Encoding.UTF8.GetBytes(uploadJson + hashString);

        DownloadHandlerBuffer d = new DownloadHandlerBuffer();
        UploadHandlerRaw u = new UploadHandlerRaw(rawBytes);
        using (UnityWebRequest unityWebRequest = new UnityWebRequest(url, "POST", d, u))
        {
            yield return unityWebRequest.SendWebRequest();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    Debug.LogError(unityWebRequest.downloadHandler.text);
                    errorCallback.Invoke();
                    break;
                case UnityWebRequest.Result.Success:
                    successCallback.Invoke();
                    break;
            }
        }
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

    string SerializeJson<T>(T value)
    {
        DataContractJsonSerializer jsonSer = new DataContractJsonSerializer(typeof(T));
        using (MemoryStream ms = new MemoryStream())
        {
            jsonSer.WriteObject(ms, value);
            ms.Position = 0;
            return new StreamReader(ms).ReadToEnd();
        }
    }
}

[DataContract]
public class EntryUpdate
{
    [DataMember]
    readonly public string name;
    [DataMember()]
    readonly public string value;
    [DataMember]
    readonly public int leaderboard_id;

    public EntryUpdate(string name, string value, int leaderboard_id)
    {
        this.name = name;
        this.value = value;
        this.leaderboard_id = leaderboard_id;
    }
}

[DataContract]
public class LeaderboardEntry
{
    [DataMember]
    readonly public string name;
    [DataMember(Name = "value")]
    readonly private string _value;
    [DataMember]
    readonly public int position;

    // If you want to parse the value yourself
    // The backend does not support strings as values
    public string GetValueAsString()
    {
        return _value;
    }

    public int GetValueAsInt()
    {
        if(int.TryParse(_value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int result))
        {
            return result;
        }
        else
        {
            return (int)Math.Round(GetValueAsDouble());
        }
    }

    public float GetValueAsFloat()
    {
        return float.Parse(_value, CultureInfo.InvariantCulture);
    }

    public double GetValueAsDouble()
    {
        return double.Parse(_value, CultureInfo.InvariantCulture);
    }
}