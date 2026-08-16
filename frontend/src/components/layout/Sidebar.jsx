import './Sidebar.css';

function Sidebar(){
    return(
        <aside className='sidebar'>
            <div>
                <h1 className='logo'>
                    <span>Glossy.</span>
                </h1>

                <button className='teamSelector'>
                    Poongcha Team
                </button>

                <nav className='menu'>
                    <button className='menuItemActive'>번역</button>
                    <button className='menuItem'>용어집</button>
                    <button className='menuItem'>상대 프로필</button>
                    <button className='menuItem'>히스토리</button>
                </nav>
            </div>

            <br />
            <nav className='settings'>
                <button className='menuItem'>내 정보</button>
                <button className='menuItem'>팀 설정</button>
            </nav>
        </aside>
    );
}

export default Sidebar;

//