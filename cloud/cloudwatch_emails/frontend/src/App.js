import './App.css';
import React, { useEffect, useState } from 'react';
import { CollapsibleList, List, SimpleListItem } from '@rmwc/list';

import '@rmwc/icon/styles';
import '@rmwc/list/styles';


const Section = ({data, icon, sectionName, useSecondary}) => {
  const copy = (text) => {
    if (document.hasFocus()) {
      navigator.clipboard.writeText(text).catch((e) => { console.log(e); });
    }
  };
  return (
    <CollapsibleList
      handle={
        <SimpleListItem
          graphic={icon}
          style={ !data.length ? { background: 'gray' } : {}}
          text={sectionName}
          metaIcon="chevron_right" />
      }>
      { !useSecondary ?
        data.map((entry, i) => (
          <SimpleListItem
            key={i}
            onClick={() => copy(entry)}
            text={entry} />)) :
        data.map((entry, i) => (
          <SimpleListItem
            key={i}
            onClick={() => copy(entry.cmd)}
            text={entry.reason}
            secondaryText={entry.cmd} />))
      }</CollapsibleList>
  )
};


const Email = (props) => {
  const { alarms, emails, system_ids } = props.body;
  const empty = !alarms.length && !emails.length && !system_ids.length;
  return (
    <CollapsibleList
      handle={
        <SimpleListItem
          graphic="email"
          style={ empty ? { background: 'gray' } : {}}
          text={props.subject}
          metaIcon="chevron_right"
        />
      }>
      <Section
        data={emails}
        icon={"person"}
        sectionName={"Emails"}/>
      <Section
        data={system_ids}
        icon={"notifications"}
        sectionName={"System IDs"}/>
      <Section
        data={alarms}
        icon={"notifications"}
        sectionName={"Alarms"}
        useSecondary={true}/>
    </CollapsibleList>
  );
};

const App = () => {
  const [emails, setEmails] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      let request = await fetch('/email_report.json');
      let data = await request.json();
      return setEmails(data);
    };
    fetchData().catch((e) => { console.log(e); });
  }, []);

  return(
    <List>
    {emails.map((email, i) => (
      <Email key={i} {...email}/>))
    }
    </List>
  );
};

export default App;
