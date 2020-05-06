package com.nx.apidoctool;

import com.nx.util.Utils;

import java.io.File;
import java.util.List;

public final class PrintDepsExecutor
    extends Executor
{
    public File vmsPath;
    /**
     * Print paths to all C++ source code and header files to be accessed, relative to vmsPath.
     */
    public int execute() throws Exception
    {
        if (!params.templateRegistrationCpp().isEmpty())
            printVmsFile(params.templateRegistrationCpp());
        for (String token: params.handlerRegistrationCpp().split(","))
            printVmsFile(token.trim());
        if (vmsPath != null && !params.typeHeaderPaths().isEmpty())
        {
            List<File> headers = Utils.getHeaderFileList(vmsPath, params.typeHeaderPaths());
            String path = vmsPath.getPath() + vmsPath.separatorChar;
            for (File header: headers)
            {
                assert header.getPath().startsWith(path);
                if (header.getPath().startsWith(path))
                    printVmsFile(header.getPath().substring(path.length()));
            }
        }
        return 1;
    }
}
