using System;

using Microsoft.VisualStudio.Coverage.Analysis;
using System.Collections.Generic;
using System.Linq.Expressions;
using System.Linq;
using System.IO;
using System.Text;

namespace CodeCoverage.CoverterConsoleApp
{
    class Program
    {
        static int Main(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Converter - reads VStest binary code coverage data, and outputs it in XML or LCOV format.");
                Console.WriteLine("Usage:  ConverageConvert <destinationfile> <sourcefile1> <sourcefile2> ... <sourcefileN>");
                return 1;
            }

            string destinationFile = args[0];

            List<string> sourceFiles = new List<string>();

            // Get all the file names EXCEPT the first one.
            for (int i = 1; i < args.Length; i++)
            {
                sourceFiles.Add(args[i]);
            }

            CoverageInfo mergedCoverage;
            try
            {
                mergedCoverage = JoinCoverageFiles(sourceFiles);
            }
            catch (Exception e)
            {
                Console.Error.WriteLine("Error opening coverage data: {0}", e.Message);
                return 1;
            }

            if (destinationFile.ToLower().EndsWith(".info"))
            {
                using (var sw = new StreamWriter(
                    File.Open(destinationFile, FileMode.Create), Encoding.UTF8))
                {
                    WriteLcov(mergedCoverage, sw);
                    return 0;
                }
            }
            
            CoverageDS data = mergedCoverage.BuildDataSet();
            try
            {
                data.WriteXml(destinationFile);
            }
            catch (Exception e)
            {

                Console.Error.WriteLine("Error writing to output file: {0}", e.Message);
                return 1;
            }

            return 0;
        }

        private static CoverageInfo JoinCoverageFiles(IEnumerable<string> files)
        {
            if (files == null)
                throw new ArgumentNullException("files");

            // This will represent the joined coverage files
            CoverageInfo returnItem = null;

            try
            {
                foreach (string sourceFile in files)
                {
                    // Create from the current file

                    string path = System.IO.Path.GetDirectoryName(sourceFile);

                    CoverageInfo current = CoverageInfo.CreateFromFile(sourceFile,
                        new string[] { path },
                        new string[] { path });

                    if (returnItem == null)
                    {
                        // First time through, assign to result
                        returnItem = current;
                        continue;
                    }

                    // Not the first time through, join the result with the current
                    CoverageInfo joined = null;
                    try
                    {
                        joined = CoverageInfo.Join(returnItem, current);
                    }
                    finally
                    {
                        // Dispose current and result
                        current.Dispose();
                        current = null;
                        returnItem.Dispose();
                        returnItem = null;
                    }

                    returnItem = joined;
                }
            }
            catch (Exception)
            {
                if (returnItem != null)
                {
                    returnItem.Dispose();
                }
                throw;
            }

            return returnItem;
        }

        private static Dictionary<BlockLineRange, CoverageStatus> BuildCoveredRangeMap(
            IList<BlockLineRange> lines,
            byte[] coverageBuffer)
        {
            var dictionary = new Dictionary<BlockLineRange, CoverageStatus>(lines.Count);
            int length = coverageBuffer.Length;
            foreach (BlockLineRange line in (IEnumerable<BlockLineRange>)lines)
            {
                if (line.IsValid)
                {
                    if ((long)line.BlockIndex >= (long)length)
                        continue;
                    CoverageStatus coverageStatus1 =
                        coverageBuffer[(int)line.BlockIndex] == (byte)0
                        ? CoverageStatus.NotCovered
                        : CoverageStatus.Covered;
                    CoverageStatus coverageStatus2;
                    dictionary[line] = 
                        !dictionary.TryGetValue(line, out coverageStatus2)
                        ? coverageStatus1
                        : (coverageStatus2 == coverageStatus1
                            ? coverageStatus2
                            : CoverageStatus.PartiallyCovered);
                }
            }
            return dictionary;
        }
        class CoverageRecord
        {
            public Dictionary<uint, string> functions = new Dictionary<uint, string>();
            public Dictionary<uint, CoverageStatus> coveredLines =
                new Dictionary<uint, CoverageStatus>();

            public void Dump(StreamWriter sw, string sourceFile)
            {
                sw.WriteLine("SF:{0}", sourceFile);
                foreach (KeyValuePair<uint, string> keyValuePair in functions)
                    sw.WriteLine("FN:{0},{1}", keyValuePair.Key, keyValuePair.Value);
                int lineHit = 0;
                foreach (KeyValuePair<uint, CoverageStatus> keyValuePair in coveredLines)
                {
                    int executionCount = keyValuePair.Value == CoverageStatus.NotCovered ? 0 : 1;
                    if (executionCount > 0)
                        lineHit++;
                    sw.WriteLine("DA:{0},{1}", keyValuePair.Key, executionCount);
                }
                sw.WriteLine("LH:{0}", lineHit);
                sw.WriteLine("LF:{0}", coveredLines.Count);
                sw.WriteLine("end_of_record");
            }

            public void AddLineCoverage(
                BlockLineRange range,
                CoverageStatus status)
            {
                for (uint startLine = range.StartLine; startLine <= range.EndLine; ++startLine)
                {
                    if (startLine == 0xFeeFee) //< Hidden line.
                        continue;
                    CoverageStatus coverageStatus;
                    coveredLines[startLine] =
                        !coveredLines.TryGetValue(startLine, out coverageStatus)
                        ? status
                        : (coverageStatus == status
                            ? coverageStatus
                            : CoverageStatus.PartiallyCovered);
                }
            }

            public void AddFunction(uint startLine, string name)
            {
                functions[startLine] = name;
            }
        };

        static void WriteLcov(CoverageInfo info, StreamWriter sw)
        {
            List<BlockLineRange> lines = new List<BlockLineRange>();

            Dictionary<string, CoverageRecord> files = new Dictionary<string, CoverageRecord>();

            foreach (ICoverageModule module in info.Modules)
            {
                byte[] coverageBuffer = module.GetCoverageBuffer(null);

                using (ISymbolReader reader = module.Symbols.CreateReader())
                {
                    uint methodId;
                    string methodName;
                    string undecoratedMethodName;
                    string className;
                    string namespaceName;

                    while (reader.GetNextMethod(
                        out methodId,
                        out methodName,
                        out undecoratedMethodName,
                        out className,
                        out namespaceName,
                        lines))
                    {
                        if (lines.Count == 0)
                            continue;

                        string sourceFile = lines.First().SourceFile;

                        CoverageRecord record = null;
                        if (!files.TryGetValue(sourceFile, out record))
                        {
                            record = new CoverageRecord();
                            files[sourceFile] = record;
                        }

                        record.AddFunction(lines.First().StartLine, methodName);

                        var dictionary = BuildCoveredRangeMap(lines, coverageBuffer);
                        foreach (KeyValuePair<BlockLineRange, CoverageStatus> keyValuePair in dictionary)
                            record.AddLineCoverage(keyValuePair.Key, keyValuePair.Value);

                        lines.Clear();
                    }
                } // ISymbolReader
            }
            // Dump coverage of all files
            foreach (KeyValuePair<string, CoverageRecord> keyValuePair in files)
                keyValuePair.Value.Dump(sw, keyValuePair.Key);
        }
    }
}
