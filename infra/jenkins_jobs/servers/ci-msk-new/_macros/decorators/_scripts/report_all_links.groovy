import hudson.FilePath
import java.io.InputStream
def platforms = manager.getEnvVariable("PLATFORMS").split(",");
def customizations = manager.getEnvVariable("CUSTOMIZATIONS").split(",");

def REPOSITORY_ROOT_URL = manager.getEnvVariable("REPOSITORY_ROOT_URL");
def JUNKSHOP_URL = manager.getEnvVariable("JUNKSHOP_URL");

def build = Thread.currentThread().executable;
def description = build.getDescription().toString();

description += "<a href='${REPOSITORY_ROOT_URL}'> Artifacts </a>, <a href='${JUNKSHOP_URL}'> Junkshop </a>"

// This is useful if we want to have link for each platform
// customizations.each { customization ->
//   platforms.each { platform ->
//     def artifactsUrl="${repositoryRoot}/${customization}/${platform}";
//     description = description + "<br><a href='${artifactsUrl}'> ${customization}@${platform} </a>";
//   }
// }

customizations.each { customization ->
  platform = "all"
  def artifactsUrl="${REPOSITORY_ROOT_URL}/${customization}/${platform}";
  description = description + "<br><a href='${artifactsUrl}'> download ${customization}/${platform} </a>";
}

build.setDescription(description);