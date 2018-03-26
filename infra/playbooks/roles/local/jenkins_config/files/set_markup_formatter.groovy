import jenkins.model.*
import hudson.markup.RawHtmlMarkupFormatter

formatter = "${formatter}"

Jenkins j = Jenkins.instance
save = false


if (formatter == "raw_html") {
  if(j.markupFormatter.class.toString() != "class hudson.markup.RawHtmlMarkupFormatter") {
    println "Current markup formatter cls is: " + j.markupFormatter.class.toString()
    j.markupFormatter = new RawHtmlMarkupFormatter(false)
    save = true
  }
}

if (formatter == "escaped_html") {
  if(j.markupFormatter.class.toString() != "class hudson.markup.EscapedMarkupFormatter") {
    println "Current markup formatter cls is: " + j.markupFormatter.class.toString()
    println "Cannot change"
  }
}

if(save) {
  j.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
