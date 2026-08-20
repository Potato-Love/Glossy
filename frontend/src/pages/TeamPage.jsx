import { Check, Copy, RefreshCw, UsersRound } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../context/authContext";
import "./PageStyles.css";

export default function TeamPage() {
  const auth = useAuth();
  const { fetchTeamMembers } = auth;
  const team = auth.currentTeam;
  const isOwner = team.role === "owner";
  const [teamName, setTeamName] = useState(team.name);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTeamName(team.name);
    setError("");
    fetchTeamMembers(team.id)
      .then(setMembers)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "팀원을 불러오지 못했습니다."));
  }, [fetchTeamMembers, team.id, team.name]);

  async function handleSaveTeam() {
    if (!teamName.trim()) return;
    setSaving(true);
    setError("");
    try {
      await auth.updateTeam(teamName);
      setMessage("팀 이름을 저장했습니다.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "팀 정보를 저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function copyInvite(value, label) {
    await navigator.clipboard.writeText(value);
    setMessage(`${label}을 복사했습니다.`);
  }

  async function handleRotate() {
    setSaving(true);
    setError("");
    try {
      await auth.rotateInviteCode();
      setMessage("새 초대 코드를 발급했습니다. 이전 코드는 더 이상 사용할 수 없습니다.");
    } catch (rotateError) {
      setError(rotateError instanceof Error ? rotateError.message : "초대 코드를 재발급하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const inviteLink = `${window.location.origin}/join/${team.invite_code || ""}`;

  return (
    <div className="page">
      <header className="page-header"><div><h1>팀 설정</h1><p>팀원과 초대 정보를 관리합니다.</p></div></header>
      {error && <div className="document-error"><span>{error}</span></div>}
      {message && <p className="status-message">{message}</p>}

      <section className="settings-section">
        <div className="section-heading"><div><h2>팀 정보</h2><p>현재 권한: {isOwner ? "소유자" : "멤버"}</p></div></div>
        <div className="inline-form">
          <div className="field"><label htmlFor="teamName">팀 이름</label><input id="teamName" className="text-field" value={teamName} onChange={(event) => setTeamName(event.target.value)} disabled={!isOwner} maxLength={50} /></div>
          {isOwner && <button className="button primary" onClick={handleSaveTeam} disabled={saving}><Check size={18} /> 저장</button>}
        </div>
      </section>

      <section className="settings-section">
        <div className="section-heading"><div><h2>팀원</h2><p>현재 팀에 참여 중인 멤버입니다.</p></div><span className="badge neutral"><UsersRound size={14} /> {members.length}명</span></div>
        <div className="data-table-wrap"><table className="data-table">
          <thead><tr><th>닉네임</th><th>소속</th><th>직책</th><th>권한</th></tr></thead>
          <tbody>{members.map((member) => <tr key={member.id}><td><strong>{member.nickname}</strong></td><td>{member.organization || "-"}</td><td>{member.position || "-"}</td><td><span className={`badge ${member.role === "owner" ? "success" : "neutral"}`}>{member.role === "owner" ? "소유자" : "멤버"}</span></td></tr>)}</tbody>
        </table></div>
      </section>

      <section className="settings-section">
        <div className="section-heading"><div><h2>팀원 초대</h2><p>{isOwner ? "코드나 링크를 공유해 팀원을 초대하세요." : "초대 정보는 팀 소유자만 관리할 수 있습니다."}</p></div></div>
        {isOwner && <div className="invite-controls">
          <div className="field"><label>초대 코드</label><div className="copy-field"><code>{team.invite_code}</code><button className="button" onClick={() => copyInvite(team.invite_code, "초대 코드")}><Copy size={16} /> 복사</button></div></div>
          <div className="field"><label>초대 링크</label><div className="copy-field"><input className="text-field" value={inviteLink} readOnly /><button className="button" onClick={() => copyInvite(inviteLink, "초대 링크")}><Copy size={16} /> 복사</button></div></div>
          <button className="button" onClick={handleRotate} disabled={saving}><RefreshCw size={16} /> 초대 코드 재발급</button>
        </div>}
      </section>
    </div>
  );
}
