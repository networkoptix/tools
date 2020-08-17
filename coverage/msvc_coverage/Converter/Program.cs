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
            for (int i = 1; i < args.Length; ++i)
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

            if (!destinationFile.ToLower().EndsWith(".xml"))
            {
                Encoding utf8WithoutBom = new UTF8Encoding(false);

                using (var stream = new StreamWriter(
                    File.Open(destinationFile, FileMode.Create), utf8WithoutBom))
                {
                    WriteLcov(mergedCoverage, stream);
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

            // This will represent the joined coverage files.
            CoverageInfo returnItem = null;

            try
            {
                foreach (string sourceFile in files)
                {
                    // Create from the current file.

                    string path = System.IO.Path.GetDirectoryName(sourceFile);

                    CoverageInfo current = CoverageInfo.CreateFromFile(sourceFile,
                        new string[] { path },
                        new string[] { path });

                    if (returnItem == null)
                    {
                        // First time through, assign to result.
                        returnItem = current;
                        continue;
                    }

                    // Not the first time through, join the result with the current.
                    CoverageInfo joined = null;
                    try
                    {
                        joined = CoverageInfo.Join(returnItem, current);
                    }
                    finally
                    {
                        // Dispose current and result.
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

        class CoverageRecord
        {
            public Dictionary<uint, string> functions = new Dictionary<uint, string>();
            public Dictionary<uint, CoverageStatus> coveredLines =
                new Dictionary<uint, CoverageStatus>();

            public void Dump(StreamWriter stream, string sourceFile)
            {
                stream.WriteLine("SF:{0}", sourceFile);
                foreach (KeyValuePair<uint, string> keyValuePair in functions)
                    stream.WriteLine("FN:{0},{1}", keyValuePair.Key, keyValuePair.Value);
                int lineHit = 0;
                foreach (KeyValuePair<uint, CoverageStatus> keyValuePair in coveredLines)
                {
                    int executionCount = keyValuePair.Value == CoverageStatus.NotCovered ? 0 : 1;
                    if (executionCount > 0)
                        ++lineHit;
                    stream.WriteLine("DA:{0},{1}", keyValuePair.Key, executionCount);
                }
                stream.WriteLine("LH:{0}", lineHit);
                stream.WriteLine("LF:{0}", coveredLines.Count);
                stream.WriteLine("end_of_record");
            }

            public void AddBlocksCoverage(
                IList<BlockLineRange> blocks,
                byte[] coverageBuffer)
            {
                int length = coverageBuffer.Length;
                foreach (BlockLineRange block in blocks)
                {
                    if (!block.IsValid)
                        continue;

                    if ((long) block.BlockIndex >= (long) length)
                        continue;

                    CoverageStatus status = coverageBuffer[(int) block.BlockIndex] == (byte) 0
                        ? CoverageStatus.NotCovered
                        : CoverageStatus.Covered;

                    AddBlockLinesCoverage(block, status);
                }
            }

            private void AddBlockLinesCoverage(
                BlockLineRange range,
                CoverageStatus status)
            {
                for (uint line = range.StartLine; line <= range.EndLine; ++line)
                {
                    if (line == 0xFeeFee) //< Hidden line.
                        continue;
                    CoverageStatus prevStatus;
                    if (!coveredLines.TryGetValue(line, out prevStatus))
                    {
                        // First time this line is counted.
                        coveredLines[line] = status;
                        continue;
                    }
                    // If the same line is Covered and NotCovered then it's PartiallyCovered.
                    if (prevStatus != status)
                        coveredLines[line] = CoverageStatus.PartiallyCovered;
                }
            }

            public void AddFunction(uint startLine, string name)
            {
                functions[startLine] = name;
            }
        };

        static void WriteLcov(CoverageInfo info, StreamWriter stream)
        {
            List<BlockLineRange> blocks = new List<BlockLineRange>();

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
                        blocks))
                    {
                        if (blocks.Count == 0)
                            continue;

                        string sourceFile = blocks.First().SourceFile;

                        CoverageRecord record = null;
                        if (!files.TryGetValue(sourceFile, out record))
                        {
                            record = new CoverageRecord();
                            files[sourceFile] = record;
                        }

                        record.AddFunction(blocks.First().StartLine, methodName);
                        record.AddBlocksCoverage(blocks, coverageBuffer);

                        blocks.Clear();
                    }
                }
            }

            // Dump coverage of all files.
            foreach (var funcCoveragePair in files)
                funcCoveragePair.Value.Dump(stream, funcCoveragePair.Key);
        }
    }
}
