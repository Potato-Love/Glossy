import { Check, Clipboard, Link2, RefreshCw, UsersRound } from "lucide-react";
import { useState } from "react";
import { useAppData } from "../context/appData";
import "./PageStyles.css";

function createInviteCode() {
  return `GLOSSY-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
}

export default function TeamPage() {
  const { team, updateTeam } = useAppData();
  const [teamName, setTeamName] = useState(team.name);
  const [copied, setCopied] = useState("");

  const inviteLink = `${window.location.origin}/onboarding?invite=${team.inviteCode}`;

  async function copyValue(value, type) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(type);
      window.setTimeout(() => setCopied(""), 1600);
    } catch {
      setCopied("error");
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><h1>팀 설정</h1><p>팀원과 초대 정보를 관리합니다.</p></div>
      </header>

      <section className="settings-section">
        <div className="section-heading"><div><h2>팀 정보</h2><p>사이드바와 팀원 화면에 표시되는 이름입니다.</p></div></div>
        <div className="inline-form">
          <div className="field"><label htmlFor="teamName">팀 이름</label><input id="teamName" className="text-field" value={teamName} onChange={(event) => setTeamName(event.target.value)} /></div>
          <button className="button primary" onClick={() => updateTeam({ name: teamName.trim() || team.name })}><Check size={18} /> 저장</button>
        </div>
      </section>

      <section className="settings-section">
        <div className="section-heading">
          <div><h2>팀원</h2><p>현재 팀에 참여 중이거나 초대된 멤버입니다.</p></div>
          <span className="badge neutral"><UsersRound size={14} /> {team.members.length}명</span>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead><tr><th>닉네임</th><th>소속</th><th>직책</th><th>상태</th></tr></thead>
            <tbody>{team.members.map((member) => <tr key={member.id}><td><strong>{member.nickname}</strong></td><td>{member.organization}</td><td>{member.position}</td><td><span className={`badge ${member.status === "활동 중" ? "success" : "neutral"}`}>{member.status}</span></td></tr>)}</tbody>
          </table>
        </div>
      </section>

      <section className="settings-section">
        <div className="section-heading">
          <div><h2>팀원 초대</h2><p>코드 또는 링크를 공유해 팀원을 초대합니다.</p></div>
          <button className="button" onClick={() => updateTeam({ inviteCode: createInviteCode() })}><RefreshCw size={17} /> 새로 생성</button>
        </div>
        <div className="form-grid">
          <div className="field full">
            <label htmlFor="inviteCodeOutput">초대 코드</label>
            <div className="copy-field"><input id="inviteCodeOutput" className="text-field" value={team.inviteCode} readOnly /><button className="button" onClick={() => copyValue(team.inviteCode, "code")}><Clipboard size={17} /> {copied === "code" ? "복사됨" : "복사"}</button></div>
          </div>
          <div className="field full">
            <label htmlFor="inviteLinkOutput">초대 링크</label>
            <div className="copy-field"><input id="inviteLinkOutput" className="text-field" value={inviteLink} readOnly /><button className="button" onClick={() => copyValue(inviteLink, "link")}><Link2 size={17} /> {copied === "link" ? "복사됨" : "복사"}</button></div>
          </div>
        </div>
        {copied === "error" && <p className="form-error">클립보드에 접근할 수 없습니다.</p>}
      </section>
    </div>
  );
}
